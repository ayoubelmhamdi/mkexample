# mkexample

Generate code snippets for various programming languages.

## Usage

```
./mkexample.py <lang> [item[=level] ...] [name=value ...]
```

## Items

| Syntax | Meaning |
|--------|---------|
| `class` | generate a minimal class |
| `class=max` | generate at specified level (`0`, `1`, `max`, `rand`) |
| `classname=Foo` | named parameter |
| `helloworld` | explicit template name |

Only list what you want — everything defaults to minimal.

## Examples

```bash
# hello world
./mkexample.py python

# minimal class
./mkexample.py cpp class

# max-complexity class with a custom name
./mkexample.py python class=max classname=MyApp

# class + doc comment at max
./mkexample.py java class doc=max classname=MyApp

# function
./mkexample.py rust fun

# class + interface together
./mkexample.py python class interface

# write to file (extension added automatically)
./mkexample.py cpp class -o myclass

# show build tool for a language
./mkexample.py c buildtool
```

## List languages / options

```bash
./mkexample.py --list-langs
./mkexample.py python --list-options
```

## Custom specs directory

```bash
./mkexample.py --specs /path/to/lang_specs python class
```
