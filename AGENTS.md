# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`modern-di-taskiq` is a taskiq integration for
[`modern-di`](https://github.com/modern-python/modern-di); [`CONTEXT.md`](CONTEXT.md) opens with
what it does and owns the vocabulary — read it before naming a concept in code, a test name, or an
issue title. It is one of that project's integrations, each of which lives in a separate repository
and ships as a separate PyPI package.

## Commands

`just` (task runner) and `uv` (package manager). The [`justfile`](justfile) is the source of truth —
`just --list`, or read it.

## Architecture

All implementation is `modern_di_taskiq/main.py`, short enough to read whole. Read it. What reading
it will not tell you is why two of its shapes are load-bearing rather than incidental: the per-task
child rides a generator `TaskiqDepends` instead of a middleware
([ADR-0001](docs/adr/0001-per-task-scope-rides-taskiq-dependencies.md)), and only the `WORKER_*`
lifecycle pair is wired
([ADR-0002](docs/adr/0002-only-worker-lifecycle-is-wired.md)).

## Workflow

Real work **not scheduled** becomes a GitHub issue.

An invariant is a test whose name is the claim, with a docstring opening `INVARIANT:` and a second
paragraph naming **what breaks it** — design rationale, not a report of what this one test catches.
Nothing enforces that docstring shape; it is read at review time.
