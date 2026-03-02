pub trait {interfacename} {
    fn greet(&self);
    fn message(&self) -> &str;
}

pub trait {interfacename}Mut: {interfacename} {
    fn set_message(&mut self, message: &str);
}