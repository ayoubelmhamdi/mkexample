public class {classname} {
    private String message;
    
    public {classname}() {
        this("Hello, World!");
    }
    
    public {classname}(String message) {
        this.message = message;
    }
    
    public String getMessage() {
        return this.message;
    }
    
    public void setMessage(String message) {
        this.message = message;
    }
    
    public void greet() {
        System.out.println(this.message);
    }
    
    public static void main(String[] args) {
        {classname} instance = new {classname}();
        instance.greet();
    }
}