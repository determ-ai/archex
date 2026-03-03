package com.example.models;

import java.time.LocalDate;

public class User {
    private String name;
    private String email;
    protected int age;
    public static final int MAX_NAME_LENGTH = 100;

    public User(String name, String email) {
        this.name = name;
        this.email = email;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    String getEmail() {
        return email;
    }

    private void validate() {
        if (name == null || name.isEmpty()) {
            throw new IllegalArgumentException("Name required");
        }
    }

    public static class Address {
        private String street;
        private String city;

        public Address(String street, String city) {
            this.street = street;
            this.city = city;
        }

        public String getStreet() {
            return street;
        }
    }
}
