package com.example.enums;

public enum Status {
    ACTIVE("active"),
    INACTIVE("inactive"),
    PENDING("pending");

    private final String label;

    Status(String label) {
        this.label = label;
    }

    public String getLabel() {
        return label;
    }
}
