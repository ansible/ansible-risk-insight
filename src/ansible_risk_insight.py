import sys
from data_container import DataContainer, config


if __name__ == "__main__":
    target_type = sys.argv[1]
    target_name = sys.argv[2]
    dependency_dir = ""
    if len(sys.argv) >= 4:
        dependency_dir = sys.argv[3]
    c = DataContainer(
        type=target_type,
        name=target_name,
        root_dir=config.data_dir,
        dependency_dir=dependency_dir,
        do_save=True
    )
    c.load()
