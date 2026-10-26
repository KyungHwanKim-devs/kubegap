# Changelog

All notable changes to kubegap are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.0] - 2026-10-27

### Added

- First release.
- Read-only audit of a Kubernetes cluster against 403 checks in 12 areas, defined as data in `collectors/*/checks.yaml` with embedded test cases.
- Two modes: `daily` with a reduced collection, compared with the previous daily run, and `full` with everything, compared with the previous full run.
- Two report files: `report.md` written for a person, with the top problems and why each happens, and `report-details.md` assembled from the snapshot.
- EKS as the baseline platform and k3s as a variant, with node access through SSM, SSH or a DaemonSet.
- Expectation profiles `prod`, `lab`, `small-prod`, `multi-az-prod` and `dev`.
- English and Korean README and sample reports.

[Unreleased]: https://github.com/KyungHwanKim-devs/kubegap/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/KyungHwanKim-devs/kubegap/releases/tag/v0.1.0
