# All functions that start with "rule_" are evaluated by risk_detector.py
# IN: tasks with "analyzed_data" (i.e. output from analyzer.py)
# OUT: matched: bool, matched_tasks: list[task | tuple of tasks], message: str
def rule_sample(tasks: list):
    # this sample rule checks if each task has a name
    matched_tasks = []
    message = ""
    # define a condition for this rule here
    for task in tasks:
        if task.get("name", "") == "":
            matched_tasks.append(task)
    message = "{} task(s) don't have the names".format(len(matched_tasks))
    # end of the condition
    matched = len(matched_tasks) > 0
    return matched, matched_tasks, message


# utility function can be defined as usual like this
def sample_utility_func(input: list):
    pass
