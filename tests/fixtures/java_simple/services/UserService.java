package com.example.services;

import com.example.models.User;
import java.util.ArrayList;
import java.util.List;

public interface UserService {
    List<User> findAll();
    User findById(int id);
    void save(User user);
}
