import argparse
from .data_container import DataContainer, config


def main():
    parser = argparse.ArgumentParser(description="TODO")
    parser.add_argument(
        "-s",
        "--save",
        action="store_true",
        help="enable file save under ARI_DATA_DIR (default=/tmp/ari-data)",
    )
    parser.add_argument(
        "target_type", help="Content type", choices={"role", "collection"}
    )
    parser.add_argument("target_name", help="Name")
    parser.add_argument("dependency_dir", nargs="?", help="TODO")

    args = parser.parse_args()

    c = DataContainer(
        type=args.target_type,
        name=args.target_name,
        root_dir=config.data_dir,
        dependency_dir=args.dependency_dir,
        do_save=args.save,
    )
    c.load()
