struct {classname} {
    message: String,
}

impl {classname} {
    fn new() -> Self {
        Self {
            message: String::from("Hello, World!"),
        }
    }
    
    fn greet(&self) {
        println!("{}", self.message);
    }
}