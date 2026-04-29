import re


class PlanLoader:
    def __init__(self, plan_file: str, resources_file: str):
        self._plan_file = plan_file
        self._resources_file = resources_file

    def _read(self, path: str) -> str:
        with open(path, encoding="utf-8") as f:
            return f.read()

    def _extract_day_section(self, text: str, day: int) -> str:
        pattern = rf"## Day {day}[\s\S]*?(?=\n## Day |\n---|\Z)"
        match = re.search(pattern, text)
        if not match:
            raise ValueError(f"Day {day} not found in {self._plan_file}")
        return match.group(0)

    def _extract_resources_section(self, text: str, day: int) -> str:
        pattern = rf"## Day {day}[\s\S]*?(?=\n## Day |\Z)"
        match = re.search(pattern, text)
        return match.group(0) if match else ""

    def load(self, day: int) -> dict:
        plan_text = self._read(self._plan_file)
        resources_text = self._read(self._resources_file)

        section = self._extract_day_section(plan_text, day)
        resources_section = self._extract_resources_section(resources_text, day)

        topic_match = re.search(r"## Day \d+[^—]*— (.+)", section)
        topic = topic_match.group(1).strip() if topic_match else f"Day {day}"

        morning_match = re.search(r"\*\*Morning.*?\*\*([\s\S]*?)(?=\*\*Afternoon|\*\*Quiz|\Z)", section)
        morning_tasks = []
        if morning_match:
            morning_tasks = [
                line.lstrip("- ").strip()
                for line in morning_match.group(1).strip().splitlines()
                if line.strip().startswith("-")
            ]

        afternoon_match = re.search(r"\*\*Afternoon.*?\*\*([\s\S]*?)(?=\*\*Quiz|\Z)", section)
        afternoon_tasks = []
        if afternoon_match:
            afternoon_tasks = [
                line.lstrip("- ").strip()
                for line in afternoon_match.group(1).strip().splitlines()
                if line.strip().startswith("-")
            ]

        quiz_match = re.search(r"\*\*Quiz.*?\*\*([\s\S]*?)(?=\*\*Review|\Z)", section)
        quiz_count = 0
        if quiz_match:
            quiz_count = len(re.findall(r"^\d+\.", quiz_match.group(1), re.MULTILINE))

        star_resources = []
        for match in re.finditer(r"★ (.+?)\. (https?://\S+)", resources_section):
            star_resources.append({"title": match.group(1).strip(), "url": match.group(2).strip()})

        return {
            "day": day,
            "topic": topic,
            "morning_tasks": morning_tasks,
            "afternoon_tasks": afternoon_tasks,
            "quiz_count": quiz_count,
            "star_resources": star_resources,
        }
