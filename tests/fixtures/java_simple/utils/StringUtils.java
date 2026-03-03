package com.example.utils;

import static java.lang.Math.max;

public final class StringUtils {
    public static final String EMPTY = "";
    private static final int DEFAULT_PAD = 4;

    private StringUtils() {}

    public static String capitalize(String input) {
        if (input == null || input.isEmpty()) {
            return input;
        }
        return Character.toUpperCase(input.charAt(0)) + input.substring(1);
    }

    public static boolean isBlank(String input) {
        return input == null || input.trim().isEmpty();
    }

    static int padSize(String input) {
        return max(DEFAULT_PAD, input.length());
    }
}
