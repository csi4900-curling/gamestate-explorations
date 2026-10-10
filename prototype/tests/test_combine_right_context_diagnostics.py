from prototype.scripts.combine_right_context_diagnostics import source_class


def test_full_match_disagreement_classes_remain_distinct():
    assert source_class("person_or_wheelchair_or_equipment") == \
        "person_or_equipment_prefix"
    assert source_class("stone_moved_by_person") == \
        "nonthrow_stone_handling_prefix"
