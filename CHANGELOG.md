# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Auto-extraction of follower/following counts from profile page
- Dynamic action calculation based on account size
- Smart scrolling to collect target users before processing
- Conservative anti-ban mode (28 actions/day max)
- Adaptive delays (30-60s between actions)

### Changed
- Actions per run now dynamic (scales with account size)
- Schedule interval adjusted to 3-6 hours for safety
- Max daily actions capped at 28 (conservative)
- 28-day expiry ensures fresh data while maintaining coverage

### Fixed
- Session import now accepts URL-encoded sessionids

## [1.0.0] - 2026-02-09

### Added
- Modular architecture with BaseFeature class
- FollowFeature: Automatically follow back users who follow you
- UnfollowFeature: Unfollow users who don't follow back
- Redis-based session persistence and scheduling
- User tracking system with 21-day expiry
- GitHub Actions CI/CD workflow
- Anti-detection measures (random delays, user agent spoofing)
- Force run capability via environment variable

### Changed
- Renamed package from IGM to IAF (Instagram Automation Framework)
- Removed password requirement (now uses cookie-based authentication)
- Updated GitHub Actions upload-artifact to v4

### Fixed
- Improved error handling with screenshots
- Better navigation timeouts
- SSL certificate verification handling

### Removed
- Direct password login (replaced with cookie-based authentication)
