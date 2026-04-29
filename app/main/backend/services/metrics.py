from dataclasses import dataclass


@dataclass
class CallMetrics:
    manager_talk_ratio: float
    client_talk_ratio: float
    interruptions: int
    avg_manager_turn_len: float
    avg_client_turn_len: float
    total_pause_sec: float
    total_duration_sec: float


def compute_metrics(turns: list[dict]) -> CallMetrics:
    if not turns:
        return CallMetrics(
            manager_talk_ratio=0,
            client_talk_ratio=0,
            interruptions=0,
            avg_manager_turn_len=0,
            avg_client_turn_len=0,
            total_pause_sec=0,
            total_duration_sec=0,
        )

    sorted_turns = sorted(turns, key=lambda t: t["t_start"])

    manager_durations: list[float] = []
    client_durations: list[float] = []
    interruptions = 0
    total_pause = 0.0

    for i, turn in enumerate(sorted_turns):
        duration = turn["t_end"] - turn["t_start"]

        if turn["speaker"] == "manager":
            manager_durations.append(duration)
        else:
            client_durations.append(duration)

        if i > 0:
            prev = sorted_turns[i - 1]
            if turn["t_start"] < prev["t_end"]:
                interruptions += 1
            else:
                total_pause += turn["t_start"] - prev["t_end"]

    total_manager = sum(manager_durations)
    total_client = sum(client_durations)
    total_speech = total_manager + total_client

    first_start = sorted_turns[0]["t_start"]
    last_end = max(t["t_end"] for t in sorted_turns)
    total_duration = last_end - first_start

    return CallMetrics(
        manager_talk_ratio=total_manager / total_speech if total_speech > 0 else 0,
        client_talk_ratio=total_client / total_speech if total_speech > 0 else 0,
        interruptions=interruptions,
        avg_manager_turn_len=total_manager / len(manager_durations) if manager_durations else 0,
        avg_client_turn_len=total_client / len(client_durations) if client_durations else 0,
        total_pause_sec=total_pause,
        total_duration_sec=total_duration,
    )
