use std::{io, fs};

pub const MAX_RETRIES: u32 = 3;

static INSTANCE_COUNT: std::sync::atomic::AtomicU32 = std::sync::atomic::AtomicU32::new(0);

pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

pub fn format_name(first: &str, last: &str) -> String {
    format!("{} {}", first, last).trim().to_string()
}

pub fn read_file(path: &str) -> io::Result<String> {
    fs::read_to_string(path)
}

macro_rules! log_debug {
    ($($arg:tt)*) => {
        #[cfg(debug_assertions)]
        eprintln!($($arg)*);
    };
}

fn internal_parse(input: &str) -> Vec<&str> {
    input.split(',').collect()
}
