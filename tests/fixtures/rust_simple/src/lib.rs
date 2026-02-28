pub mod models;
pub mod utils;

use std::io;

pub fn initialize() -> io::Result<()> {
    Ok(())
}

pub trait Processor {
    fn process(&self, input: &str) -> String;
    fn validate(&self, input: &str) -> bool;
}

pub trait Serializable {
    fn serialize(&self) -> Vec<u8>;
}

fn internal_helper() -> bool {
    true
}
