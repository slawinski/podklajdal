from io import StringIO

from podklajdal.services.separator import _TqdmProgressStream


def test_tqdm_progress_is_captured_without_forwarding_raw_bar() -> None:
    progress: list[int] = []
    fallback = StringIO()
    stream = _TqdmProgressStream(progress.append, fallback)

    stream.write("\r  1%|#7 | 1/102 [00:06<10:43, 6.37s/it]")
    stream.write("\r 10%|################9 | 10/102 [00:42<06:11, 4.04s/it]")
    stream.write("\n")

    assert progress == [1, 10]
    assert fallback.getvalue() == ""


def test_non_progress_stderr_is_preserved() -> None:
    fallback = StringIO()
    stream = _TqdmProgressStream(lambda percent: None, fallback)

    stream.write("warning from separator\n")

    assert fallback.getvalue() == "warning from separator\n"
