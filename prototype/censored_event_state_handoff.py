"""Join moving pixels, view censoring, and later partial image boards."""

from copy import deepcopy


def _indexed(rows):
    indexed = {row["right_proposal_id"]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("Duplicate right proposal ID")
    return indexed


def build_censored_event_state_handoff(body_links, partial_state, boundary):
    if (body_links["lowres_source_sha256"] != partial_state["source_sha256"]
            or body_links["highres_source_sha256"] != boundary[
                "source_video_sha256"] or
            body_links["source_interval_s"] != partial_state["interval_s"]):
        raise ValueError("Source fingerprint or interval differs")
    linked = _indexed(body_links["rows"])
    boards = _indexed(partial_state["rows"])
    tails = _indexed(boundary["paths"])
    if set(linked) != set(boards):
        raise ValueError("Right proposal inventory differs")
    stone_ids = {key for key, row in linked.items() if
                 row["source_prefix_class"] == "moving_stone_pixels"}
    if set(tails) != stone_ids:
        raise ValueError("Boundary coverage differs from reviewed stone paths")
    witnessed_id = boundary["selected_A401_source_frame_witness"][
        "right_proposal_id"]
    if witnessed_id not in stone_ids:
        raise ValueError("Boundary witness is not a reviewed stone path")
    output = []
    for proposal_id, board in boards.items():
        link = linked[proposal_id]
        if (link["episode_id"] != board["episode_id"] or
                link["colour_claim"] != board["colour_claim"] or
                link["source_prefix_class"] != board["source_prefix_class"]):
            raise ValueError("Joined right proposal differs")
        is_stone_pixels = proposal_id in stone_ids
        motion = None
        terminal = None
        if is_stone_pixels:
            if (link["body_path_status"] != "unique_compatible_body_path" or
                    len(link["compatible_highres_paths"]) != 1):
                raise ValueError("High-resolution moving body path is ambiguous")
            tail = tails[proposal_id]
            if (tail["colour_claim"] != link["colour_claim"] or
                    tail["last_saved_moving_source_time_s"] != link[
                        "compatible_highres_paths"][0][
                            "highres_handle_supported_moving_points"][-1][
                                "time_s"]):
                raise ValueError("Boundary tail differs from moving body path")
            points = link["compatible_highres_paths"][0][
                "highres_handle_supported_moving_points"]
            if tail["last_saved_body_center_1080p_px"] != points[-1][
                    "center_1080p_px"]:
                raise ValueError("Terminal body center differs")
            motion = {"camera": "right_1080p",
                      "coordinate_frame": "source_image_pixels_not_metric_ice",
                      "body_centers": [{"source_time_s": point["time_s"],
                                        "center_1080p_px": point[
                                            "center_1080p_px"]}
                                       for point in points],
                      "physical_stone_identity_verified": False}
            screen = tail["next_second_colour_screen"]
            terminal = {
                "last_saved_body_observation_s": tail[
                    "last_saved_moving_source_time_s"],
                "last_saved_body_center_1080p_px": tail[
                    "last_saved_body_center_1080p_px"],
                "next_second_colour_screen": deepcopy(screen),
                "old_body_search_bottom_y_exclusive": boundary[
                    "highres_body_search_bottom_y_exclusive"],
                "source_frame_bottom_y_exclusive": boundary[
                    "source_frame_bottom_y_exclusive"],
                "selected_source_frame_boundary_contact_then_absence": (
                    proposal_id == witnessed_id),
                "physical_settle_inferred": False,
                "same_stone_continuation_verified": False,
                "observation_terminal_status":
                    "camera_local_observation_censored_or_unresolved",
            }
        elif (link["source_prefix_class"] != "person_or_clothing_pixels" or
              board["following_partial_image_observation"] is not None):
            raise ValueError("Nonstone path or board differs")
        observed_board = deepcopy(board["following_partial_image_observation"])
        if observed_board is not None and observed_board[
                "complete_board_verified"] is not False:
            raise ValueError("Complete board was unexpectedly claimed")
        output.append({
            "right_proposal_id": proposal_id,
            "episode_id": link["episode_id"],
            "passage_time_s": board["passage_time_s"],
            "source_prefix_class": link["source_prefix_class"],
            "colour_claim": link["colour_claim"],
            "observed_moving_pixels": motion,
            "terminal_visibility": terminal,
            "following_partial_image_board": observed_board,
            "following_partial_image_board_status": board["state_status"],
            "physical_throw_verified": False,
            "physical_release_time_s": None,
            "physical_settle_time_s": None,
            "same_stone_to_board_verified": False,
            "complete_post_throw_board": None,
            "metric_trajectory": None,
            "spin_revolution_count": None,
            "simulation_ready": False,
            "simulation_blockers": [
                "physical_event_identity_unverified",
                "full_trajectory_censored_or_unobserved",
                "physical_settle_time_unknown",
                "same_stone_to_partial_board_unverified",
                "complete_metric_board_unavailable",
                "spin_unknown",
            ],
        })
    output.sort(key=lambda row: (row["passage_time_s"],
                                 row["right_proposal_id"]))
    return output
