"""Parse official Paralympic shot-order text without video predictions."""

import re


ROTATIONS = {"↻": "clockwise", "↺": "counter_clockwise"}


def parse_shot_page(text, teams):
    if "Game - Shot by Shot" not in text:
        raise ValueError("Not a shot-by-shot page")
    match = re.search(r"(?m)^End (\d+)$", text)
    if not match:
        raise ValueError("Missing end number")
    end_number = int(match.group(1))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    scores = {}
    header_order = [
        line.split(" - ", 1)[0]
        for line in lines
        if "(this end)" in line and any(line.startswith(f"{team} - ") for team in teams)
    ]
    if len(header_order) != 2 or set(header_order) != set(teams):
        raise ValueError("Missing or duplicate team score headers")
    for team in teams:
        header = next(
            (line for line in lines if line.startswith(f"{team} - ") and "(this end)" in line), None
        )
        if header is None:
            raise ValueError(f"Missing {team} end header")
        result = re.search(r"\+\s*(\d+|X)\s*\(this end\)\s*=\s*(\d+)", header)
        if result is None:
            raise ValueError(f"Invalid {team} score header")
        scores[team] = {"this_end": result.group(1), "total_after_end": int(result.group(2))}
    shots = []
    for index, line in enumerate(lines):
        team = next((name for name in teams if line.startswith(f"{name}: ")), None)
        if team is None:
            continue
        shooter = line[len(team) + 2 :]
        if not shooter:
            raise ValueError("Missing shooter")
        number_index = index + 1
        while (
            number_index < len(lines)
            and not re.fullmatch(r"\d{1,2}", lines[number_index])
            and number_index - index <= 3
        ):
            number_index += 1
        if (
            number_index >= len(lines)
            or number_index - index > 3
            or not re.fullmatch(r"\d{1,2}", lines[number_index])
        ):
            raise ValueError(f"Missing shot number after {line}")
        notes = lines[index + 1 : number_index]
        if lines[index - 1] in ROTATIONS:
            rotation = ROTATIONS[lines[index - 1]]
            percentage = lines[index - 2]
            shot_type = lines[index - 3]
        elif lines[index - 1] == "-":
            rotation = None
            percentage = None
            shot_type = lines[index - 2]
        else:
            raise ValueError(f"Missing rotation or no-score mark before {line}")
        if percentage is not None and not re.fullmatch(r"\d+%", percentage):
            raise ValueError(f"Invalid shot score before {line}")
        shots.append(
            {
                "shot_number": int(lines[number_index]),
                "team": team,
                "shooter": shooter,
                "shot_type": shot_type,
                "evaluation_percent": int(percentage[:-1]) if percentage else None,
                "rotation": rotation,
                "notes": notes,
            }
        )
    numbers = [shot["shot_number"] for shot in shots]
    if not shots or numbers != list(range(1, len(shots) + 1)):
        raise ValueError("Shot numbers are not contiguous from one")
    if len(shots) > 16:
        raise ValueError("More than 16 shots in an end")
    for before, after in zip(shots, shots[1:]):
        if before["team"] == after["team"]:
            raise ValueError("Official shots do not alternate teams")
    return {
        "end": end_number,
        "header_team_order": header_order,
        "team_scores": scores,
        "shot_count": len(shots),
        "shots": shots,
    }
