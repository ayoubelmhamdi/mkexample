class {classname}{extends_clause}
{
private:
    std::string message_;

public:
    {classname}() : message_("Hello, World!") { }
    explicit {classname}(const std::string& message) : message_(message) { }
    virtual ~{classname}() = default;
    
    const std::string& getMessage() const { return message_; }
    void setMessage(const std::string& message) { message_ = message; }
    
    virtual void {methodname}() {
        std::cout << message_ << std::endl;
    }
};