class {interfacename}
{
public:
    virtual ~{interfacename}() = default;
    virtual void {methodname}() = 0;
    virtual const std::string& getMessage() const = 0;
};
