
# Equipment Tracking

* [Introduction](#introduction)
* [Defining a New Item](#defining-a-new-item)
* [Adding Parts](#adding-parts)

## Introduction

### Bike Components

I keep forgetting to track when I modify equipment on my bike.  This
is annoying, because I would like to know if certain models of
components (chains, particularly) last longer than others.

So I wanted to make a solution that made my life as simple as
possible.  The result is a command line tool where I can type

    > ch2 kit add cotic chain pc1110

when I add a SRAM PC1110 chain to my Cotic bike, and everything else
is done for me, automatically.

If I want statistics on chains, I can type:

    > ch2 kit statistics chain

If I want statistics on that particular model:

    > ch2 kit statistics pc1110

### Shoes

I'm not so bothered about shoes, but I know many runners are, and
supporting them was my second use case.

Unlike bike components, buying a second pair of shoes doesn't
necessarily replace the first pair.  So you have to expire these
automatically:

    > ch2 new shoe ultraboost-19
    > ch2 new shoe zoom-pegasus
    > ch2 retire ultraboost-19
    > ch2 statistics shoe

### Making Things General

Choochoo can track *anything* that fits into this schema:

    **Groups** These are the *kinds of things* you track: shoes,
    bikes, etc.

    **Items** These are the particular things: the name you give to a
    particular bike, or a particular pair of shoes.

    **Components** These (optionally) make up the things you are
    tracking.  So "chain", for a bike, or "shoelaces" (maybe!) for
    shoes.

    **Models* These describe a particular component.  So the chain
    migbt be "PC1110".

Note that all these anmes can contain spaces, but if you use spaces
you need to take care with quotes on the command line.  I find it's
simpler to use dashes.

Also, names must be unique.  You cannot re-use the same name for
different things.

### An Example

First, I will add my Cotic bike:

    > ch2 kit new bike cotic --force
    Traceback (most recent call last):
      File "/usr/local/lib/python3.7/runpy.py", line 183, in _run_module_as_main
        mod_name, mod_spec, code = _get_module_details(mod_name, _Error)
      File "/usr/local/lib/python3.7/runpy.py", line 142, in _get_module_details
        return _get_module_details(pkg_main_name, error)
      File "/usr/local/lib/python3.7/runpy.py", line 109, in _get_module_details
        __import__(pkg_name)
      File "/home/andrew/project/ch2/choochoo/ch2/__init__.py", line 22, in <module>
        from .commands.activities import activities
      File "/home/andrew/project/ch2/choochoo/ch2/commands/activities.py", line 3, in <module>
        from ..squeal import PipelineType
      File "/home/andrew/project/ch2/choochoo/ch2/squeal/__init__.py", line 4, in <module>
        from .tables.kit import KitGroup, KitItem, KitComponent, KitModel
      File "/home/andrew/project/ch2/choochoo/ch2/squeal/tables/kit.py", line 73, in <module>
        class KitItem(Source):
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/api.py", line 75, in __init__
        _as_declarative(cls, classname, cls.__dict__)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 131, in _as_declarative
        _MapperConfig.setup_mapping(cls, classname, dict_)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 160, in setup_mapping
        cfg_cls(cls_, classname, dict_)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 194, in __init__
        self._early_mapping()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 199, in _early_mapping
        self.map()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 696, in map
        self.cls, self.local_table, **self.mapper_args
      File "<string>", line 2, in mapper
      File "<string>", line 2, in __init__
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/util/deprecations.py", line 128, in warned
        return fn(*args, **kwargs)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/orm/mapper.py", line 710, in __init__
        self._configure_inheritance()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/orm/mapper.py", line 1033, in _configure_inheritance
        self.inherits.local_table, self.local_table
      File "<string>", line 2, in join_condition
      File "<string>", line 2, in _join_condition
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/util/deprecations.py", line 128, in warned
        return fn(*args, **kwargs)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/sql/selectable.py", line 947, in _join_condition
        % (a.description, b.description, hint)
    sqlalchemy.exc.NoForeignKeysError: Can't find any foreign key relationships between 'source' and 'kit_item'.


We're introducing a completely new *group* (bike) and so the `--force`
flag is needed for confirmation.  Adding future bikes will not require
this, because `bike` will already be known by the system..

Now I have a bike I am going to add some inner tubes at various dates.

    > ch2 kit add cotic front-tube michelin 2019-01-01 --force
    Traceback (most recent call last):
      File "/usr/local/lib/python3.7/runpy.py", line 183, in _run_module_as_main
        mod_name, mod_spec, code = _get_module_details(mod_name, _Error)
      File "/usr/local/lib/python3.7/runpy.py", line 142, in _get_module_details
        return _get_module_details(pkg_main_name, error)
      File "/usr/local/lib/python3.7/runpy.py", line 109, in _get_module_details
        __import__(pkg_name)
      File "/home/andrew/project/ch2/choochoo/ch2/__init__.py", line 22, in <module>
        from .commands.activities import activities
      File "/home/andrew/project/ch2/choochoo/ch2/commands/activities.py", line 3, in <module>
        from ..squeal import PipelineType
      File "/home/andrew/project/ch2/choochoo/ch2/squeal/__init__.py", line 4, in <module>
        from .tables.kit import KitGroup, KitItem, KitComponent, KitModel
      File "/home/andrew/project/ch2/choochoo/ch2/squeal/tables/kit.py", line 73, in <module>
        class KitItem(Source):
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/api.py", line 75, in __init__
        _as_declarative(cls, classname, cls.__dict__)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 131, in _as_declarative
        _MapperConfig.setup_mapping(cls, classname, dict_)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 160, in setup_mapping
        cfg_cls(cls_, classname, dict_)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 194, in __init__
        self._early_mapping()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 199, in _early_mapping
        self.map()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 696, in map
        self.cls, self.local_table, **self.mapper_args
      File "<string>", line 2, in mapper
      File "<string>", line 2, in __init__
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/util/deprecations.py", line 128, in warned
        return fn(*args, **kwargs)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/orm/mapper.py", line 710, in __init__
        self._configure_inheritance()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/orm/mapper.py", line 1033, in _configure_inheritance
        self.inherits.local_table, self.local_table
      File "<string>", line 2, in join_condition
      File "<string>", line 2, in _join_condition
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/util/deprecations.py", line 128, in warned
        return fn(*args, **kwargs)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/sql/selectable.py", line 947, in _join_condition
        % (a.description, b.description, hint)
    sqlalchemy.exc.NoForeignKeysError: Can't find any foreign key relationships between 'source' and 'kit_item'.


Again the system catches the first use of `front-tube` so we flag that
it is OK with `--force`.

    > ch2 kit add cotic front-tube michelin 2019-03-01
    Traceback (most recent call last):
      File "/usr/local/lib/python3.7/runpy.py", line 183, in _run_module_as_main
        mod_name, mod_spec, code = _get_module_details(mod_name, _Error)
      File "/usr/local/lib/python3.7/runpy.py", line 142, in _get_module_details
        return _get_module_details(pkg_main_name, error)
      File "/usr/local/lib/python3.7/runpy.py", line 109, in _get_module_details
        __import__(pkg_name)
      File "/home/andrew/project/ch2/choochoo/ch2/__init__.py", line 22, in <module>
        from .commands.activities import activities
      File "/home/andrew/project/ch2/choochoo/ch2/commands/activities.py", line 3, in <module>
        from ..squeal import PipelineType
      File "/home/andrew/project/ch2/choochoo/ch2/squeal/__init__.py", line 4, in <module>
        from .tables.kit import KitGroup, KitItem, KitComponent, KitModel
      File "/home/andrew/project/ch2/choochoo/ch2/squeal/tables/kit.py", line 73, in <module>
        class KitItem(Source):
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/api.py", line 75, in __init__
        _as_declarative(cls, classname, cls.__dict__)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 131, in _as_declarative
        _MapperConfig.setup_mapping(cls, classname, dict_)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 160, in setup_mapping
        cfg_cls(cls_, classname, dict_)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 194, in __init__
        self._early_mapping()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 199, in _early_mapping
        self.map()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 696, in map
        self.cls, self.local_table, **self.mapper_args
      File "<string>", line 2, in mapper
      File "<string>", line 2, in __init__
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/util/deprecations.py", line 128, in warned
        return fn(*args, **kwargs)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/orm/mapper.py", line 710, in __init__
        self._configure_inheritance()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/orm/mapper.py", line 1033, in _configure_inheritance
        self.inherits.local_table, self.local_table
      File "<string>", line 2, in join_condition
      File "<string>", line 2, in _join_condition
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/util/deprecations.py", line 128, in warned
        return fn(*args, **kwargs)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/sql/selectable.py", line 947, in _join_condition
        % (a.description, b.description, hint)
    sqlalchemy.exc.NoForeignKeysError: Can't find any foreign key relationships between 'source' and 'kit_item'.


    > ch2 kit add cotic front-tube vittoria
    Traceback (most recent call last):
      File "/usr/local/lib/python3.7/runpy.py", line 183, in _run_module_as_main
        mod_name, mod_spec, code = _get_module_details(mod_name, _Error)
      File "/usr/local/lib/python3.7/runpy.py", line 142, in _get_module_details
        return _get_module_details(pkg_main_name, error)
      File "/usr/local/lib/python3.7/runpy.py", line 109, in _get_module_details
        __import__(pkg_name)
      File "/home/andrew/project/ch2/choochoo/ch2/__init__.py", line 22, in <module>
        from .commands.activities import activities
      File "/home/andrew/project/ch2/choochoo/ch2/commands/activities.py", line 3, in <module>
        from ..squeal import PipelineType
      File "/home/andrew/project/ch2/choochoo/ch2/squeal/__init__.py", line 4, in <module>
        from .tables.kit import KitGroup, KitItem, KitComponent, KitModel
      File "/home/andrew/project/ch2/choochoo/ch2/squeal/tables/kit.py", line 73, in <module>
        class KitItem(Source):
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/api.py", line 75, in __init__
        _as_declarative(cls, classname, cls.__dict__)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 131, in _as_declarative
        _MapperConfig.setup_mapping(cls, classname, dict_)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 160, in setup_mapping
        cfg_cls(cls_, classname, dict_)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 194, in __init__
        self._early_mapping()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 199, in _early_mapping
        self.map()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 696, in map
        self.cls, self.local_table, **self.mapper_args
      File "<string>", line 2, in mapper
      File "<string>", line 2, in __init__
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/util/deprecations.py", line 128, in warned
        return fn(*args, **kwargs)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/orm/mapper.py", line 710, in __init__
        self._configure_inheritance()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/orm/mapper.py", line 1033, in _configure_inheritance
        self.inherits.local_table, self.local_table
      File "<string>", line 2, in join_condition
      File "<string>", line 2, in _join_condition
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/util/deprecations.py", line 128, in warned
        return fn(*args, **kwargs)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/sql/selectable.py", line 947, in _join_condition
        % (a.description, b.description, hint)
    sqlalchemy.exc.NoForeignKeysError: Can't find any foreign key relationships between 'source' and 'kit_item'.


That's three different inner tubes on the front.  The last uses
today's date as a default - that makes it easy to note changes at the
command line as you do the work.

Previous tubes are *retired* as new ones are added.  You don't need to
add the tubes in order - however they're added, the start and end
times should align correctly.

    > ch2 kit add cotic front-tube michelin 2019-01-01
    Traceback (most recent call last):
      File "/usr/local/lib/python3.7/runpy.py", line 183, in _run_module_as_main
        mod_name, mod_spec, code = _get_module_details(mod_name, _Error)
      File "/usr/local/lib/python3.7/runpy.py", line 142, in _get_module_details
        return _get_module_details(pkg_main_name, error)
      File "/usr/local/lib/python3.7/runpy.py", line 109, in _get_module_details
        __import__(pkg_name)
      File "/home/andrew/project/ch2/choochoo/ch2/__init__.py", line 22, in <module>
        from .commands.activities import activities
      File "/home/andrew/project/ch2/choochoo/ch2/commands/activities.py", line 3, in <module>
        from ..squeal import PipelineType
      File "/home/andrew/project/ch2/choochoo/ch2/squeal/__init__.py", line 4, in <module>
        from .tables.kit import KitGroup, KitItem, KitComponent, KitModel
      File "/home/andrew/project/ch2/choochoo/ch2/squeal/tables/kit.py", line 73, in <module>
        class KitItem(Source):
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/api.py", line 75, in __init__
        _as_declarative(cls, classname, cls.__dict__)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 131, in _as_declarative
        _MapperConfig.setup_mapping(cls, classname, dict_)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 160, in setup_mapping
        cfg_cls(cls_, classname, dict_)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 194, in __init__
        self._early_mapping()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 199, in _early_mapping
        self.map()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 696, in map
        self.cls, self.local_table, **self.mapper_args
      File "<string>", line 2, in mapper
      File "<string>", line 2, in __init__
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/util/deprecations.py", line 128, in warned
        return fn(*args, **kwargs)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/orm/mapper.py", line 710, in __init__
        self._configure_inheritance()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/orm/mapper.py", line 1033, in _configure_inheritance
        self.inherits.local_table, self.local_table
      File "<string>", line 2, in join_condition
      File "<string>", line 2, in _join_condition
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/util/deprecations.py", line 128, in warned
        return fn(*args, **kwargs)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/sql/selectable.py", line 947, in _join_condition
        % (a.description, b.description, hint)
    sqlalchemy.exc.NoForeignKeysError: Can't find any foreign key relationships between 'source' and 'kit_item'.


    > ch2 kit new bike cotic
    Traceback (most recent call last):
      File "/usr/local/lib/python3.7/runpy.py", line 183, in _run_module_as_main
        mod_name, mod_spec, code = _get_module_details(mod_name, _Error)
      File "/usr/local/lib/python3.7/runpy.py", line 142, in _get_module_details
        return _get_module_details(pkg_main_name, error)
      File "/usr/local/lib/python3.7/runpy.py", line 109, in _get_module_details
        __import__(pkg_name)
      File "/home/andrew/project/ch2/choochoo/ch2/__init__.py", line 22, in <module>
        from .commands.activities import activities
      File "/home/andrew/project/ch2/choochoo/ch2/commands/activities.py", line 3, in <module>
        from ..squeal import PipelineType
      File "/home/andrew/project/ch2/choochoo/ch2/squeal/__init__.py", line 4, in <module>
        from .tables.kit import KitGroup, KitItem, KitComponent, KitModel
      File "/home/andrew/project/ch2/choochoo/ch2/squeal/tables/kit.py", line 73, in <module>
        class KitItem(Source):
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/api.py", line 75, in __init__
        _as_declarative(cls, classname, cls.__dict__)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 131, in _as_declarative
        _MapperConfig.setup_mapping(cls, classname, dict_)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 160, in setup_mapping
        cfg_cls(cls_, classname, dict_)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 194, in __init__
        self._early_mapping()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 199, in _early_mapping
        self.map()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/ext/declarative/base.py", line 696, in map
        self.cls, self.local_table, **self.mapper_args
      File "<string>", line 2, in mapper
      File "<string>", line 2, in __init__
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/util/deprecations.py", line 128, in warned
        return fn(*args, **kwargs)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/orm/mapper.py", line 710, in __init__
        self._configure_inheritance()
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/orm/mapper.py", line 1033, in _configure_inheritance
        self.inherits.local_table, self.local_table
      File "<string>", line 2, in join_condition
      File "<string>", line 2, in _join_condition
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/util/deprecations.py", line 128, in warned
        return fn(*args, **kwargs)
      File "/home/andrew/project/ch2/choochoo/env/lib/python3.7/site-packages/sqlalchemy/sql/selectable.py", line 947, in _join_condition
        % (a.description, b.description, hint)
    sqlalchemy.exc.NoForeignKeysError: Can't find any foreign key relationships between 'source' and 'kit_item'.


