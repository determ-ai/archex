use std::collections::HashMap;
use crate::models::{User, Role};
use crate::utils::format_name;

mod models;
mod utils;

fn main() {
    let users: HashMap<String, User> = HashMap::new();
    let name = format_name("Alice", "Smith");
    println!("Hello, {}!", name);
}

fn setup_logging() {
    env_logger::init();
}
