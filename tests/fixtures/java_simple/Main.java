package com.example;

import com.example.models.User;
import com.example.services.UserService;
import java.util.List;

public class Main {
    public static void main(String[] args) {
        UserService service = new UserService();
        List<User> users = service.findAll();
        System.out.println(users);
    }
}
