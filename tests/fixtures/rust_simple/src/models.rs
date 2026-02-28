use std::fmt;
use super::utils::format_name;

#[derive(Debug, Clone)]
pub struct User {
    pub name: String,
    pub email: String,
    role: Role,
}

impl User {
    pub fn new(name: String, email: String) -> Self {
        Self {
            name,
            email,
            role: Role::Viewer,
        }
    }

    pub fn display_name(&self) -> String {
        format_name(&self.name, "")
    }

    fn validate_email(email: &str) -> bool {
        email.contains('@')
    }
}

impl fmt::Display for User {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} <{}>", self.name, self.email)
    }
}

pub enum Role {
    Admin,
    Editor,
    Viewer,
}

pub(crate) struct Config {
    pub database_url: String,
    pub port: u16,
}

impl Config {
    pub(crate) fn default_port() -> u16 {
        8080
    }
}

pub struct Pagination<T> {
    pub items: Vec<T>,
    pub total: usize,
}
