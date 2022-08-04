import argparse
import os
import json
import jsonpickle
import logging
from struct5 import get_object, Module, Task, TaskFile, Role, RoleInPlay, Playbook, Play, Collection, ObjectList


class Grapher():
    def __init__(self, dir="", out_dir=""):
        self.dir = dir
        self.out_dir = out_dir
        if self.dir != "" and self.out_dir == "":
            self.out_dir = self.dir

        self.in_module_file = os.path.join(self.dir, "modules.json")
        self.in_role_file = os.path.join(self.dir, "roles.json")
        self.in_taskfile_file = os.path.join(self.dir, "taskfiles.json")
        self.in_playbook_file = os.path.join(self.dir, "playbooks.json")
        self.in_play_file = os.path.join(self.dir, "plays.json")
        self.in_task_file = os.path.join(self.dir, "tasks.json")

        self.out_graph_file = os.path.join(self.out_dir, "graph.json")

    def run(self):
        self.graph()
        return

    def graph(self):
        graph_lines = []
        logging.debug("making playbook graph")
        graph_lines.extend(self.playbook_graph())
        logging.debug("making play graph")
        graph_lines.extend(self.play_graph())
        logging.debug("making role graph")
        graph_lines.extend(self.role_graph())
        logging.debug("making taskfile graph")
        graph_lines.extend(self.taskfile_graph())
        logging.debug("making task graph")
        graph_lines.extend(self.task_graph())
        data = "\n".join(graph_lines)
        with open(self.out_graph_file, "w") as file:
            file.write(data)

    def playbook_graph(self):
        graph_lines = []
        playbooks = ObjectList().from_json(fpath=self.in_playbook_file)
        for p in playbooks.items:
            if not isinstance(p, Playbook):
                continue
            src_key = p.key
            if src_key == "":
                continue
            dst_keys = [play for play in p.plays]
            for dst_key in dst_keys:
                graph_line = json.dumps([src_key, dst_key])
                graph_lines.append(graph_line)
        return graph_lines

    def play_graph(self):
        graph_lines = []
        plays = ObjectList().from_json(fpath=self.in_play_file)
        for p in plays.items:
            if not isinstance(p, Play):
                continue
            src_key = p.key
            if src_key == "":
                continue
            dst_keys = []
            if p.import_playbook != "":
                playbook_path = os.path.normpath(os.path.join(os.path.dirname(p.defined_in), p.import_playbook))
                playbook_key = "Playbook {}".format(playbook_path)
                dst_keys.append(playbook_key)
            for t in p.pre_tasks:
                dst_keys.append(t)
            for t in p.tasks:
                dst_keys.append(t)
            for t in p.post_tasks:
                dst_keys.append(t)
            for rip in p.roles:
                if not isinstance(rip, RoleInPlay):
                    continue
                if rip.resolved_name == "":
                    continue
                role_key = "Role {}".format(rip.resolved_name)
                dst_keys.append(role_key)
            for dst_key in dst_keys:
                graph_line = json.dumps([src_key, dst_key])
                graph_lines.append(graph_line)
        return graph_lines
    
    def role_graph(self):
        graph_lines = []
        roles = ObjectList().from_json(fpath=self.in_role_file)
        for r in roles.items:
            if not isinstance(r, Role):
                continue
            src_key = r.key
            if src_key == "":
                continue
            dst_keys = []
            # only main.yml is recorded as graph for role
            # other taskfiles will be called from the main.yml
            main_taskfile = [tf for tf in r.taskfiles if os.path.basename(tf.replace("TaskFile ", "")) in ["main.yml", "main.yaml"]]
            dst_keys.extend(main_taskfile)
            for dst_key in dst_keys:
                graph_line = json.dumps([src_key, dst_key])
                graph_lines.append(graph_line)
        return graph_lines

    def taskfile_graph(self):
        graph_lines = []
        taskfiles = ObjectList().from_json(fpath=self.in_taskfile_file)
        for tf in taskfiles.items:
            if not isinstance(tf, TaskFile):
                continue
            src_key = tf.key
            if src_key == "":
                continue
            dst_keys = [t for t in tf.tasks]
            for dst_key in dst_keys:
                graph_line = json.dumps([src_key, dst_key])
                graph_lines.append(graph_line)
        return graph_lines

    def task_graph(self):
        graph_lines = []
        tasks = ObjectList().from_json(fpath=self.in_task_file)
        for t in tasks.items:
            if not isinstance(t, Task):
                continue
            src_key = t.key
            if src_key == "":
                continue
            exec_type = t.executable_type
            if exec_type == "":
                continue
            resolved_name = t.resolved_name
            if resolved_name == "":
                continue
            dst_key = "{} {}".format(exec_type, resolved_name)
            graph_line = json.dumps([src_key, dst_key])
            graph_lines.append(graph_line)
        return graph_lines

def main():
    parser = argparse.ArgumentParser(
        prog='graph.py',
        description='make graph',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-m', '--mode', default="definition", help='mode')
    parser.add_argument('-d', '--dir', default="", help='path to input directory')
    parser.add_argument('-o', '--out-dir', default="", help='path to the output directory')
    
    args = parser.parse_args()
    m = Grapher(args.mode, args.dir, args.out_dir)
    m.run()


if __name__ == "__main__":
    main()