import json
from ansible_risk_insight import ARIScanner, Config
import os

if __name__ == "__main__":
    playbook_path = os.path.join(os.path.dirname(__file__), "playbooks/sample_playbook.yml")
    rule_dir = os.path.join(os.path.dirname(__file__), "rules")
    task_name = "Create a cloud instance"
    rule_id = "Sample101"

    ariScanner = ARIScanner(
        Config(
            rules_dir=rule_dir,
            data_dir="/tmp/ari-data",
            rules=[
                "P001",  # need for module annotation
                "P002",  # need for module annotation
                "P003",  # need for module annotation
                "P004",  # need for module annotation
                rule_id,
            ],
        ),
        silent=True,
    )

    if not playbook_path:
        print("please input file path to scan")
    else:
        result = ariScanner.evaluate(
            type="playbook",
            path=playbook_path,
        )

        playbook = result.playbook(path=playbook_path)
        if not playbook:
            raise ValueError("the playbook was not found")

        # to get all tasks
        # tasks = playbook.tasks()

        # to get a task with specific name
        task = playbook.task(task_name)
        if not task:
            raise ValueError("No task was found")

        rule_result = task.find_result(rule_id=rule_id)
        # rule_result = task.find_result(rule_id="P001")

        if not rule_result:
            raise ValueError("the rule result was not found")

        if rule_result.error:
            raise ValueError(f"the rule could not be evaluated: {rule_result.error}")

        detail_dict = rule_result.get_detail()
        print(json.dumps(detail_dict, indent=2))
