from app.tts import split_runs


def test_mixed_text_is_split_by_script():
    runs = split_runs("Hello दोस्तों, आज हम meeting में project discuss करेंगे.")
    assert runs == [
        ("en", "Hello"),
        ("hi", "दोस्तों, आज हम"),
        ("en", "meeting"),
        ("hi", "में"),
        ("en", "project discuss"),
        ("hi", "करेंगे."),
    ]


def test_pure_english_is_one_run():
    assert split_runs("Just English here.") == [("en", "Just English here.")]


def test_punctuation_only_is_dropped():
    assert split_runs(" ... ") == []
