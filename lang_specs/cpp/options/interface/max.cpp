#include <iostream>
#include <string>

/*
 * {interfacename} is used as an interface.
 *
 * Why?
 * - It contains a pure virtual function ({methodname}() = 0).
 * - It cannot be instantiated.
 * - It defines behavior only, no data members.
 * - It has a virtual destructor for proper polymorphic cleanup.
 *
 * In C++, abstract classes with only pure virtual functions
 * are used to model interfaces (since C++ has no "interface" keyword).
 */
class {interfacename}
{
public:
    virtual ~{interfacename}() = default;   // Virtual destructor for safe polymorphism
    virtual void {methodname}() = 0;        // Pure virtual function → makes class abstract
};


/*
 * {classname} is NOT an interface.
 *
 * Why?
 * - It has data members (message_).
 * - It has constructors.
 * - {methodname}() is virtual but NOT pure virtual.
 * - It can be instantiated.
 *
 * Therefore, {classname} is a concrete class that supports polymorphism,
 * but it is not an interface.
 */
class {classname}
{
private:
    std::string message_;  // State → interfaces typically don't contain state

public:
    {classname}() : message_("Hello, World!") {}
    explicit {classname}(const std::string& message) : message_(message) {}
    virtual ~{classname}() = default;

    const std::string& getMessage() const { return message_; }
    void setMessage(const std::string& message) { message_ = message; }

    // Virtual, but NOT pure → class is still concrete
    virtual void {methodname}() {
        std::cout << message_ << std::endl;
    }
};


/*
 * {classname} implements the {interfacename} interface.
 *
 * Because {interfacename} has a pure virtual function,
 * {classname} must override {methodname}() to be instantiable.
 */
class {classname} : public {interfacename}
{
private:
    std::string name_;

public:
    explicit {classname}(const std::string& name) : name_(name) {}

    void {methodname}() override
    {
        std::cout << "Hello, " << name_ << "!" << std::endl;
    }
};


int main()
{
    // Using {classname} (concrete class)
    {classname} obj("Hi from {classname}");
    obj.{methodname}();

    // Using {classname} through interface pointer (polymorphism)
    {interfacename}* greeter = new {classname}("Alice");
    greeter->{methodname}();
    delete greeter;

    return 0;
}
