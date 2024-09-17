"""Utility helpers to simplify working with yaml-based data."""

# pylint: disable=too-many-lines
from __future__ import annotations

import functools
import re
from collections.abc import Callable, Iterator, Sequence
from io import StringIO
from pathlib import Path
from re import Pattern
from typing import TYPE_CHECKING, Any, cast

import ruamel.yaml.events
from ruamel.yaml.comments import CommentedMap, CommentedSeq, Format
from ruamel.yaml.composer import ComposerError
from ruamel.yaml.constructor import RoundTripConstructor
from ruamel.yaml.emitter import Emitter

# Module 'ruamel.yaml' does not explicitly export attribute 'YAML'; implicit reexport disabled
# To make the type checkers happy, we import from ruamel.yaml.main instead.
from ruamel.yaml.main import YAML
from ruamel.yaml.parser import ParserError
from ruamel.yaml.scalarint import HexInt, ScalarInt
from ansiblelint.constants import (
    ANNOTATION_KEYS
)
from ansiblelint.utils import Task
import ansible_risk_insight.logger as logger


if TYPE_CHECKING:
    # noinspection PyProtectedMember
    from ruamel.yaml.compat import StreamTextType
    from ruamel.yaml.nodes import ScalarNode
    from ruamel.yaml.representer import RoundTripRepresenter
    from ruamel.yaml.tokens import CommentToken


def nested_items_path(
    data_collection: dict[Any, Any] | list[Any],
    ignored_keys: Sequence[str] = (),
) -> Iterator[tuple[Any, Any, list[str | int]]]:
    """Iterate a nested data structure, yielding key/index, value, and parent_path.

    This is a recursive function that calls itself for each nested layer of data.
    Each iteration yields:

    1. the current item's dictionary key or list index,
    2. the current item's value, and
    3. the path to the current item from the outermost data structure.

    For dicts, the yielded (1) key and (2) value are what ``dict.items()`` yields.
    For lists, the yielded (1) index and (2) value are what ``enumerate()`` yields.
    The final component, the parent path, is a list of dict keys and list indexes.
    The parent path can be helpful in providing error messages that indicate
    precisely which part of a yaml file (or other data structure) needs to be fixed.

    For example, given this playbook:

    .. code-block:: yaml

        - name: A play
          tasks:
          - name: A task
            debug:
              msg: foobar

    Here's the first and last yielded items:

    .. code-block:: python

        >>> playbook=[{"name": "a play", "tasks": [{"name": "a task", "debug": {"msg": "foobar"}}]}]
        >>> next( nested_items_path( playbook ) )
        (0, {'name': 'a play', 'tasks': [{'name': 'a task', 'debug': {'msg': 'foobar'}}]}, [])
        >>> list( nested_items_path( playbook ) )[-1]
        ('msg', 'foobar', [0, 'tasks', 0, 'debug'])

    Note that, for outermost data structure, the parent path is ``[]`` because
    you do not need to descend into any nested dicts or lists to find the indicated
    key and value.

    If a rule were designed to prohibit "foobar" debug messages, it could use the
    parent path to provide a path to the problematic ``msg``. It might use a jq-style
    path in its error message: "the error is at ``.[0].tasks[0].debug.msg``".
    Or if a utility could automatically fix issues, it could use the path to descend
    to the parent object using something like this:

    .. code-block:: python

        target = data
        for segment in parent_path:
            target = target[segment]

    :param data_collection: The nested data (dicts or lists).

    :returns: each iteration yields the key (of the parent dict) or the index (lists)
    """
    # As typing and mypy cannot effectively ensure we are called only with
    # valid data, we better ignore NoneType
    if data_collection is None:
        return
    data: dict[Any, Any] | list[Any]
    if isinstance(data_collection, Task):
        data = data_collection.normalized_task
    else:
        data = data_collection
    yield from _nested_items_path(
        data_collection=data,
        parent_path=[],
        ignored_keys=ignored_keys,
    )


def _nested_items_path(
    data_collection: dict[Any, Any] | list[Any],
    parent_path: list[str | int],
    ignored_keys: Sequence[str] = (),
) -> Iterator[tuple[Any, Any, list[str | int]]]:
    """Iterate through data_collection (internal implementation of nested_items_path).

    This is a separate function because callers of nested_items_path should
    not be using the parent_path param which is used in recursive _nested_items_path
    calls to build up the path to the parent object of the current key/index, value.
    """
    # we have to cast each convert_to_tuples assignment or mypy complains
    # that both assignments (for dict and list) do not have the same type
    convert_to_tuples_type = Callable[[], Iterator[tuple[str | int, Any]]]
    if isinstance(data_collection, dict):
        convert_data_collection_to_tuples = cast(
            convert_to_tuples_type,
            functools.partial(data_collection.items),
        )
    elif isinstance(data_collection, list):
        convert_data_collection_to_tuples = cast(
            convert_to_tuples_type,
            functools.partial(enumerate, data_collection),
        )
    else:
        msg = f"Expected a dict or a list but got {data_collection!r} of type '{type(data_collection)}'"
        raise TypeError(msg)
    for key, value in convert_data_collection_to_tuples():
        if key in (*ANNOTATION_KEYS, *ignored_keys):
            continue
        yield key, value, parent_path
        if isinstance(value, dict | list):
            yield from _nested_items_path(
                data_collection=value,
                parent_path=[*parent_path, key],
            )


class OctalIntYAML11(ScalarInt):
    """OctalInt representation for YAML 1.1."""

    # tell mypy that ScalarInt has these attributes
    _width: Any
    _underscore: Any

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        """Create a new int with ScalarInt-defined attributes."""
        return ScalarInt.__new__(cls, *args, **kwargs)

    @staticmethod
    def represent_octal(representer: RoundTripRepresenter, data: OctalIntYAML11) -> Any:
        """Return a YAML 1.1 octal representation.

        Based on ruamel.yaml.representer.RoundTripRepresenter.represent_octal_int()
        (which only handles the YAML 1.2 octal representation).
        """
        v = format(data, "o")
        anchor = data.yaml_anchor(any=True)
        # noinspection PyProtectedMember
        return representer.insert_underscore(
            "0",
            v,
            data._underscore,  # noqa: SLF001
            anchor=anchor,
        )


class CustomConstructor(RoundTripConstructor):
    """Custom YAML constructor that preserves Octal formatting in YAML 1.1."""

    def construct_yaml_int(self, node: ScalarNode) -> Any:
        """Construct int while preserving Octal formatting in YAML 1.1.

        ruamel.yaml only preserves the octal format for YAML 1.2.
        For 1.1, it converts the octal to an int. So, we preserve the format.

        Code partially copied from ruamel.yaml (MIT licensed).
        """
        ret = super().construct_yaml_int(node)
        if self.resolver.processing_version == (1, 1) and isinstance(ret, int):
            # Do not rewrite zero as octal.
            if ret == 0:
                return ret
            # see if we've got an octal we need to preserve.
            value_su = self.construct_scalar(node)
            try:
                v = value_su.rstrip("_")
                underscore = [len(v) - v.rindex("_") - 1, False, False]  # type: Any
            except ValueError:
                underscore = None
            except IndexError:
                underscore = None
            value_s = value_su.replace("_", "")
            if value_s[0] in "+-":
                value_s = value_s[1:]
            if value_s[0:2] == "0x":
                ret = HexInt(ret, width=len(value_s) - 2)
            elif value_s[0] == "0":
                # got an octal in YAML 1.1
                ret = OctalIntYAML11(
                    ret,
                    width=None,
                    underscore=underscore,
                    anchor=node.anchor,
                )
        return ret


CustomConstructor.add_constructor(
    "tag:yaml.org,2002:int",
    CustomConstructor.construct_yaml_int,
)


class FormattedEmitter(Emitter):
    """Emitter that applies custom formatting rules when dumping YAML.

    Differences from ruamel.yaml defaults:

      - indentation of root-level sequences
      - prefer double-quoted scalars over single-quoted scalars

    This ensures that root-level sequences are never indented.
    All subsequent levels are indented as configured (normal ruamel.yaml behavior).

    Earlier implementations used dedent on ruamel.yaml's dumped output,
    but string magic like that had a ton of problematic edge cases.
    """

    preferred_quote = '"'  # either " or '

    min_spaces_inside = 0
    max_spaces_inside = 1

    _sequence_indent = 2
    _sequence_dash_offset = 0  # Should be _sequence_indent - 2
    _root_is_sequence = False

    _in_empty_flow_map = False

    # "/n/n" results in one blank line (end the previous line, then newline).
    # So, "/n/n/n" or more is too many new lines. Clean it up.
    _re_repeat_blank_lines: Pattern[str] = re.compile(r"\n{3,}")

    @staticmethod
    def drop_octothorpe_protection(string: str) -> str:
        """Remove string protection of "#" after full-line-comment post-processing."""
        try:
            if "\uFF03#\uFE5F" in string:
                # # is \uFF03 (fullwidth number sign)
                # ﹟ is \uFE5F (small number sign)
                string = string.replace("\uFF03#\uFE5F", "#")
        except (ValueError, TypeError):
            # probably not really a string. Whatever.
            pass
        return string

    # comment is a CommentToken, not Any (Any is ruamel.yaml's lazy type hint).
    def write_comment(
        self,
        comment: CommentToken,
        pre: bool = False,  # noqa: FBT002
    ) -> None:
        """Clean up extra new lines and spaces in comments.

        ruamel.yaml treats new or empty lines as comments.
        See: https://stackoverflow.com/questions/42708668/removing-all-blank-lines-but-not-comments-in-ruamel-yaml/42712747#42712747
        """
        value: str = comment.value
        if (
            pre
            and not value.strip()
            and not isinstance(
                self.event,
                ruamel.yaml.events.CollectionEndEvent
                | ruamel.yaml.events.DocumentEndEvent
                | ruamel.yaml.events.StreamEndEvent
                | ruamel.yaml.events.MappingStartEvent,
            )
        ):
            # drop pure whitespace pre comments
            # does not apply to End events since they consume one of the newlines.
            value = ""
        elif (
            pre
            and not value.strip()
            and isinstance(self.event, ruamel.yaml.events.MappingStartEvent)
        ):
            value = self._re_repeat_blank_lines.sub("", value)
        elif pre:
            # preserve content in pre comment with at least one newline,
            # but no extra blank lines.
            value = self._re_repeat_blank_lines.sub("\n", value)
        else:
            # single blank lines in post comments
            value = self._re_repeat_blank_lines.sub("\n\n", value)
        comment.value = value

        # make sure that the eol comment only has one space before it.
        if comment.column > self.column + 1 and not pre:
            comment.column = self.column + 1

        return super().write_comment(comment, pre)

    def write_version_directive(self, version_text: Any) -> None:
        """Skip writing '%YAML 1.1'."""
        if version_text == "1.1":
            return
        super().write_version_directive(version_text)


# pylint: disable=too-many-instance-attributes
class FormattedYAML(YAML):
    """A YAML loader/dumper that handles ansible content better by default."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        *,
        typ: str | None = None,
        pure: bool = False,
        output: Any = None,
        plug_ins: list[str] | None = None,
        version: tuple[int, int] | None = None,
    ):
        """Return a configured ``ruamel.yaml.YAML`` instance.

        Some config defaults get extracted from the yamllint config.

        ``ruamel.yaml.YAML`` uses attributes to configure how it dumps yaml files.
        Some of these settings can be confusing, so here are examples of how different
        settings will affect the dumped yaml.

        This example does not indent any sequences:

        .. code:: python

            yaml.explicit_start=True
            yaml.map_indent=2
            yaml.sequence_indent=2
            yaml.sequence_dash_offset=0

        .. code:: yaml

            ---
            - name: A playbook
              tasks:
              - name: Task

        This example indents all sequences including the root-level:

        .. code:: python

            yaml.explicit_start=True
            yaml.map_indent=2
            yaml.sequence_indent=4
            yaml.sequence_dash_offset=2
            # yaml.Emitter defaults to ruamel.yaml.emitter.Emitter

        .. code:: yaml

            ---
              - name: Playbook
                tasks:
                  - name: Task

        This example indents all sequences except at the root-level:

        .. code:: python

            yaml.explicit_start=True
            yaml.map_indent=2
            yaml.sequence_indent=4
            yaml.sequence_dash_offset=2
            yaml.Emitter = FormattedEmitter  # custom Emitter prevents root-level indents

        .. code:: yaml

            ---
            - name: Playbook
              tasks:
                - name: Task
        """
        if version:
            if isinstance(version, str):
                x, y = version.split(".", maxsplit=1)
                version = (int(x), int(y))
            self._yaml_version_default: tuple[int, int] = version
            self._yaml_version: tuple[int, int] = self._yaml_version_default
        super().__init__(typ=typ, pure=pure, output=output, plug_ins=plug_ins)

        # NB: We ignore some mypy issues because ruamel.yaml typehints are not great.

        # config = self._defaults_from_yamllint_config()

        # # these settings are derived from yamllint config
        # self.explicit_start: bool = config["explicit_start"]  # type: ignore[assignment]
        # self.explicit_end: bool = config["explicit_end"]  # type: ignore[assignment]
        # self.width: int = config["width"]  # type: ignore[assignment]
        # indent_sequences: bool = cast(bool, config["indent_sequences"])
        # preferred_quote: str = cast(str, config["preferred_quote"])  # either ' or "

        # min_spaces_inside: int = cast(int, config["min_spaces_inside"])
        # max_spaces_inside: int = cast(int, config["max_spaces_inside"])

        self.default_flow_style = False
        self.compact_seq_seq = True  # type: ignore[assignment] # dash after dash
        self.compact_seq_map = True  # type: ignore[assignment] # key after dash

        # Do not use yaml.indent() as it obscures the purpose of these vars:
        self.map_indent = 2
        self.sequence_indent = 2
        self.sequence_dash_offset = self.sequence_indent - 2

        # If someone doesn't want our FormattedEmitter, they can change it.
        self.Emitter = FormattedEmitter

        # ignore invalid preferred_quote setting

        FormattedEmitter.preferred_quote = '"'
        # NB: default_style affects preferred_quote as well.
        # self.default_style ∈ None (default), '', '"', "'", '|', '>'

        # spaces inside braces for flow mappings
        FormattedEmitter.min_spaces_inside = 0
        FormattedEmitter.max_spaces_inside = 1

        # We need a custom constructor to preserve Octal formatting in YAML 1.1
        self.Constructor = CustomConstructor
        self.Representer.add_representer(OctalIntYAML11, OctalIntYAML11.represent_octal)

        # We should preserve_quotes loads all strings as a str subclass that carries
        # a quote attribute. Will the str subclasses cause problems in transforms?
        # Are there any other gotchas to this?
        #
        # This will only preserve quotes for strings read from the file.
        # anything modified by the transform will use no quotes, preferred_quote,
        # or the quote that results in the least amount of escaping.

        # If needed, we can use this to change null representation to be explicit
        # (see https://stackoverflow.com/a/44314840/1134951)
        # self.Representer.add_representer(

    @property
    def version(self) -> tuple[int, int] | None:
        """Return the YAML version used to parse or dump.

        Ansible uses PyYAML which only supports YAML 1.1. ruamel.yaml defaults to 1.2.
        So, we have to make sure we dump yaml files using YAML 1.1.
        We can relax the version requirement once ansible uses a version of PyYAML
        that includes this PR: https://github.com/yaml/pyyaml/pull/555
        """
        if hasattr(self, "_yaml_version"):
            return self._yaml_version
        return None

    @version.setter
    def version(self, value: tuple[int, int] | None) -> None:
        """Ensure that yaml version uses our default value.

        The yaml Reader updates this value based on the ``%YAML`` directive in files.
        So, if a file does not include the directive, it sets this to None.
        But, None effectively resets the parsing version to YAML 1.2 (ruamel's default).
        """
        if value is not None:
            self._yaml_version = value
        elif hasattr(self, "_yaml_version_default"):
            self._yaml_version = self._yaml_version_default
        # We do nothing if the object did not have a previous default version defined

    def load(self, stream: Path | StreamTextType) -> Any:
        """Load YAML content from a string while avoiding known ruamel.yaml issues."""
        if not isinstance(stream, str):
            msg = f"expected a str but got {type(stream)}"
            raise NotImplementedError(msg)
        # As ruamel drops comments for any document that is not a mapping or sequence,
        # we need to avoid using it to reformat those documents.
        # https://sourceforge.net/p/ruamel-yaml/tickets/460/

        text, preamble_comment = self._pre_process_yaml(stream)
        try:
            data = super().load(stream=text)
        except ComposerError:
            data = self.load_all(stream=text)
        except ParserError as ex:
            data = None
            logger.error(  # noqa: TRY400
                "Invalid yaml, verify the file contents and try again. %s", ex
            )
        except Exception as ex:
            logger.error(  # noqa: TRY400
                "Yaml load failed with exception: %s", ex
            )
        if preamble_comment is not None and isinstance(
            data,
            CommentedMap | CommentedSeq,
        ):
            data.preamble_comment = preamble_comment  # type: ignore[union-attr]
        # Because data can validly also be None for empty documents, we cannot
        # really annotate the return type here, so we need to remember to
        # never save None or scalar data types when reformatting.
        return data

    def dumps(self, data: Any) -> str:
        """Dump YAML document to string (including its preamble_comment)."""
        preamble_comment: str | None = getattr(data, "preamble_comment", None)
        self._prevent_wrapping_flow_style(data)
        with StringIO() as stream:
            if preamble_comment:
                stream.write(preamble_comment)
            self.dump(data, stream)
            text = stream.getvalue()
        strip_version_directive = hasattr(self, "_yaml_version_default")
        return self._post_process_yaml(
            text,
            strip_version_directive=strip_version_directive,
        )

    def _prevent_wrapping_flow_style(self, data: Any) -> None:
        if not isinstance(data, CommentedMap | CommentedSeq):
            return
        for key, value, parent_path in nested_items_path(data):
            if not isinstance(value, CommentedMap | CommentedSeq):
                continue
            fa: Format = value.fa
            if fa.flow_style():
                predicted_indent = self._predict_indent_length(parent_path, key)
                predicted_width = len(str(value))
                if predicted_indent + predicted_width > self.width:
                    # this flow-style map will probably get line-wrapped,
                    # so, switch it to block style to avoid the line wrap.
                    fa.set_block_style()

    def _predict_indent_length(self, parent_path: list[str | int], key: Any) -> int:
        indent = 0

        # each parent_key type tells us what the indent is for the next level.
        for parent_key in parent_path:
            if isinstance(parent_key, int) and indent == 0:
                # root level is a sequence
                indent += self.sequence_dash_offset
            elif isinstance(parent_key, int):
                # next level is a sequence
                indent += cast(int, self.sequence_indent)
            elif isinstance(parent_key, str):
                # next level is a map
                indent += cast(int, self.map_indent)

        if isinstance(key, int) and indent == 0:
            # flow map is an item in a root-level sequence
            indent += self.sequence_dash_offset
        elif isinstance(key, int) and indent > 0:
            # flow map is in a sequence
            indent += cast(int, self.sequence_indent)
        elif isinstance(key, str):
            # flow map is in a map
            indent += len(key + ": ")

        return indent

    # ruamel.yaml only preserves empty (no whitespace) blank lines
    # (ie "/n/n" becomes "/n/n" but "/n  /n" becomes "/n").
    # So, we need to identify whitespace-only lines to drop spaces before reading.
    _whitespace_only_lines_re = re.compile(r"^ +$", re.MULTILINE)

    def _pre_process_yaml(self, text: str) -> tuple[str, str | None]:
        """Handle known issues with ruamel.yaml loading.

        Preserve blank lines despite extra whitespace.
        Preserve any preamble (aka header) comments before "---".

        For more on preamble comments, see:
        https://stackoverflow.com/questions/70286108/python-ruamel-yaml-package-how-to-get-header-comment-lines/70287507#70287507
        """
        text = self._whitespace_only_lines_re.sub("", text)

        # I investigated extending ruamel.yaml to capture preamble comments.
        #   preamble comment goes from:
        #     DocumentStartToken.comment -> DocumentStartEvent.comment
        #   Then, in the composer:
        #     once in composer.current_event
        #         discards DocumentStartEvent
        #           move DocumentStartEvent to composer.last_event
        #             all document nodes get composed (events get used)
        #         discard DocumentEndEvent
        #           move DocumentEndEvent to composer.last_event
        # So, there's no convenient way to extend the composer
        # to somehow capture the comments and pass them on.

        preamble_comments = []
        if "\n---\n" not in text and "\n--- " not in text:
            # nothing is before the document start mark,
            # so there are no comments to preserve.
            return text, None
        for line in text.splitlines(True):
            # We only need to capture the preamble comments. No need to remove them.
            # lines might also include directives.
            if line.lstrip().startswith("#") or line == "\n":
                preamble_comments.append(line)
            elif line.startswith("---"):
                break

        return text, "".join(preamble_comments) or None

    @staticmethod
    def _post_process_yaml(text: str, *, strip_version_directive: bool = False) -> str:
        """Handle known issues with ruamel.yaml dumping.

        Make sure there's only one newline at the end of the file.

        Fix the indent of full-line comments to match the indent of the next line.
        See: https://stackoverflow.com/questions/71354698/how-can-i-use-the-ruamel-yaml-rtsc-mode/71355688#71355688
        Also, removes "#" protection from strings that prevents them from being
        identified as full line comments in post-processing.

        Make sure null list items don't end in a space.
        """
        # remove YAML directive
        if strip_version_directive and text.startswith("%YAML"):
            text = text.split("\n", 1)[1]

        text = text.rstrip("\n") + "\n"

        lines = text.splitlines(keepends=True)
        full_line_comments: list[tuple[int, str]] = []
        for i, line in enumerate(lines):
            stripped = line.lstrip()
            if not stripped:
                # blank line. Move on.
                continue

            space_length = len(line) - len(stripped)

            if stripped.startswith("#"):
                # got a full line comment

                # allow some full line comments to match the previous indent
                if i > 0 and not full_line_comments and space_length:
                    prev = lines[i - 1]
                    prev_space_length = len(prev) - len(prev.lstrip())
                    if prev_space_length == space_length:
                        # if the indent matches the previous line's indent, skip it.
                        continue

                full_line_comments.append((i, stripped))
            elif full_line_comments:
                # end of full line comments so adjust to match indent of this line
                spaces = " " * space_length
                for index, comment in full_line_comments:
                    lines[index] = spaces + comment
                full_line_comments.clear()

            cleaned = line.strip()
            if not cleaned.startswith("#") and cleaned.endswith("-"):
                # got an empty list item. drop any trailing spaces.
                lines[i] = line.rstrip() + "\n"

        text = "".join(
            FormattedEmitter.drop_octothorpe_protection(line) for line in lines
        )
        return text
