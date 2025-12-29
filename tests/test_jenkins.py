from yardmaster.services.jenkins import JenkinsService


def test_build_job_url_nested_path() -> None:
    svc = JenkinsService(url="http://jenkins.example", username=None, token=None)
    url = svc._build_job_url("container/release")
    assert url == "http://jenkins.example/job/container/job/release/buildWithParameters"


def test_build_pr_version_uses_channel_from_minor() -> None:
    version = JenkinsService._build_pr_version("3600.1.0", "flatcar-master")
    assert version == "beta-3600.1.101-flatcar-master"


def test_build_pr_version_uses_main_channel() -> None:
    version = JenkinsService._build_pr_version("3600.2.0", "main")
    assert version == "main-3600.2.101-main"
