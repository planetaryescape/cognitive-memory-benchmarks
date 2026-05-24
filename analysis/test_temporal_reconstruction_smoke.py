from analysis.temporal_reconstruction_smoke import run_smoke


def test_temporal_reconstruction_smoke_passes():
    result = run_smoke()

    assert result["status"] == "pass"
    assert all(result["checks"].values())
