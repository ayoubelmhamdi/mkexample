class {classname}{extends_clause}
{
private:
    std::string message_;

public:
    {classname}() : message_("Hello, World!") { }
    
    void {methodname}() {
        std::cout << message_ << std::endl;
    }
};