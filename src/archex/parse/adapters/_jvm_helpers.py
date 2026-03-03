"""Shared helpers for JVM language adapters (Java, Kotlin)."""

from __future__ import annotations

import os
from enum import StrEnum

from archex.models import Visibility


class JvmConvention(StrEnum):
    MAVEN = "maven"
    GRADLE = "gradle"
    FLAT = "flat"


def detect_jvm_convention(file_map: dict[str, str]) -> JvmConvention:
    """Detect Maven/Gradle/flat project layout from file paths."""
    for key in file_map:
        normalized = key.replace("\\", "/")
        if "/src/main/java/" in normalized or normalized.startswith("src/main/java/"):
            return JvmConvention.MAVEN
        if "/app/src/main/java/" in normalized or "/app/src/main/kotlin/" in normalized:
            return JvmConvention.GRADLE
    return JvmConvention.FLAT


def resolve_jvm_import(
    import_path: str,
    file_map: dict[str, str],
    extensions: tuple[str, ...] = (".java",),
) -> str | None:
    """Resolve a JVM import path to a local file.

    Maps ``com.example.Foo`` → searches for ``Foo.java`` (or ``.kt``) in a
    matching directory structure within *file_map*.
    """
    parts = import_path.split(".")
    if not parts:
        return None

    # The last segment is the class name
    class_name = parts[-1]
    # Wildcard imports can't resolve to a single file
    if class_name == "*":
        return None

    package_parts = parts[:-1]

    for ext in extensions:
        target_file = class_name + ext
        candidates: list[tuple[int, str]] = []

        for key, abs_path in file_map.items():
            basename = os.path.basename(key)
            if basename != target_file:
                continue
            dir_path = os.path.dirname(key).replace("\\", "/")
            dir_segments = [s for s in dir_path.split("/") if s]

            # Score: how many trailing package parts match the directory
            score = 0
            for i, pkg_part in enumerate(reversed(package_parts)):
                idx = len(dir_segments) - 1 - i
                if idx >= 0 and dir_segments[idx] == pkg_part:
                    score += 1
                else:
                    break

            candidates.append((score, abs_path))

        if candidates:
            # Return the best-matching candidate
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]

    return None


def map_jvm_visibility(
    modifier: str | None, default: Visibility = Visibility.INTERNAL
) -> Visibility:
    """Map a JVM access modifier keyword to a Visibility enum value."""
    if modifier is None:
        return default
    modifier = modifier.strip().lower()
    if modifier == "public":
        return Visibility.PUBLIC
    if modifier == "protected":
        return Visibility.INTERNAL
    if modifier == "private":
        return Visibility.PRIVATE
    if modifier == "internal":
        return Visibility.INTERNAL
    return default
