pub struct {classname} {
    message: String,
}

impl Default for {classname} {
    fn default() -> Self {
        Self::new()
    }
}

impl {classname} {
    pub fn new() -> Self {
        Self {
            message: String::from("Hello, World!"),
        }
    }
    
    pub fn with_message(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
    
    pub fn greet(&self) {
        println!("{}", self.message);
    }
    
    pub fn message(&self) -> &str {
        &self.message
    }
}