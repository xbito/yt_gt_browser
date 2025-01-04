- You can assume Python 3.12
- Ensure your code is clean and well-documented.
- Follow PEP 8 style guide for Python code.
- Include docstrings for all functions and classes.
- Avoid premature optimization; focus on readability first.


The following section is a map of the NiceGUI namespace and its contents.
It is not exhaustive, but it gives you a good idea of what is available.

#### `ui`

UI elements and other essentials to run a NiceGUI app.

- `ui.element`: base class for all UI elements
    - customization:
        - `.props()` and `.default_props()`: add Quasar props and regular HTML attributes
        - `.classes()` and `.default_classes()`: add Quasar, Tailwind and custom HTML classes
        - `.tailwind`: convenience API for adding Tailwind classes
        - `.style()` and `.default_style()`: add CSS style definitions
        - `.tooltip()`: add a tooltip to an element
        - `.mark()`: mark an element for querying with an [ElementFilter](/documentation/element_filter)
    - interaction:
        - `.on()`: add Python and JavaScript event handlers
        - `.update()`: send an update to the client (mostly done automatically)
        - `.run_method()`: run a method on the client side
        - `.get_computed_prop()`: get the value of a property that is computed on the client side
    - hierarchy:
        - `with ...:` nesting elements in a declarative way
        - `__iter__`: an iterator over all child elements
        - `ancestors`: an iterator over the element's parent, grandparent, etc.
        - `descendants`: an iterator over all child elements, grandchildren, etc.
        - `slots`: a dictionary of named slots
        - `add_slot`: fill a new slot with NiceGUI elements or a scoped slot with template strings
        - `clear`: remove all child elements
        - `move`: move an element to a new parent
        - `remove`: remove a child element
        - `delete`: delete an element and all its children
        - `is_deleted`: whether an element has been deleted
- elements:
    - `ui.aggrid`
    - `ui.audio`
    - `ui.avatar`
    - `ui.badge`
    - `ui.button`
    - `ui.button_group`
    - `ui.card`, `ui.card_actions`, `ui.card_section`
    - `ui.carousel`, `ui.carousel_slide`
    - `ui.chat_message`
    - `ui.checkbox`
    - `ui.chip`
    - `ui.circular_progress`
    - `ui.code`
    - `ui.codemirror`
    - `ui.color_input`
    - `ui.color_picker`
    - `ui.column`
    - `ui.context_menu`
    - `ui.date`
    - `ui.dialog`
    - `ui.dropdown_button`
    - `ui.echart`
    - `ui.editor`
    - `ui.expansion`
    - `ui.grid`
    - `ui.highchart`
    - `ui.html`
    - `ui.icon`
    - `ui.image`
    - `ui.input`
    - `ui.interactive_image`
    - `ui.item`, `ui.item_label`, `ui.item_section`
    - `ui.joystick`
    - `ui.json_editor`
    - `ui.knob`
    - `ui.label`
    - `ui.leaflet`
    - `ui.line_plot`
    - `ui.linear_progress`
    - `ui.link`, `ui.link_target`
    - `ui.list`
    - `ui.log`
    - `ui.markdown`
    - `ui.matplotlib`
    - `ui.menu`, `ui.menu_item`
    - `ui.mermaid`
    - `ui.notification`
    - `ui.number`
    - `ui.pagination`
    - `ui.plotly`
    - `ui.pyplot`
    - `ui.radio`
    - `ui.range`
    - `ui.restructured_text`
    - `ui.row`
    - `ui.scene`, `ui.scene_view`
    - `ui.scroll_area`
    - `ui.select`
    - `ui.separator`
    - `ui.skeleton`
    - `ui.slider`
    - `ui.space`
    - `ui.spinner`
    - `ui.splitter`
    - `ui.step`, `ui.stepper`, `ui.stepper_navigation`
    - `ui.switch`
    - `ui.tabs`, `ui.tab`, `ui.tab_panels`, `ui.tab_panel`
    - `ui.table`
    - `ui.textarea`
    - `ui.time`
    - `ui.timeline`, `ui.timeline_entry`
    - `ui.toggle`
    - `ui.tooltip`
    - `ui.tree`
    - `ui.upload`
    - `ui.video`
- special layout elements
    - `ui.header`
    - `ui.footer`
    - `ui.drawer`, `ui.left_drawer`, `ui.right_drawer`
    - `ui.page_sticky`
- special functions and objects:
    - `ui.add_body_html` and `ui.add_head_html`: add HTML to the body and head of the page
    - `ui.add_css`, `ui.add_sass` and `ui.add_scss`: add CSS, SASS and SCSS to the page
    - `ui.clipboard`: interact with the browser's clipboard
    - `ui.colors`: define the main color theme for a page
    - `ui.context`: get the current UI context including the `client` and `request` objects
    - `ui.dark_mode`: get and set the dark mode on a page
    - `ui.download`: download a file to the client
    - `ui.keyboard`: define keyboard event handlers
    - `ui.navigate`: let the browser navigate to another location
    - `ui.notify`: show a notification
    - `ui.on`: register an event handler
    - `ui.page_title`: change the current page title
    - `ui.query`: query HTML elements on the client side to modify props, classes and style definitions
    - `ui.run` and `ui.run_with`: run the app (standalone or attached to a FastAPI app)
    - `ui.run_javascript`: run custom JavaScript on the client side (can use `getElement()`, `getHtmlElement()`, and `emitEvent()`)
    - `ui.teleport`: teleport an element to a different location in the HTML DOM
    - `ui.timer`: run a function periodically or once after a delay
    - `ui.update`: send updates of multiple elements to the client
- decorators:
    - `ui.page`: define a page (in contrast to the automatically generated "auto-index page")
    - `ui.refreshable`, `ui.refreshable_method`: define refreshable UI containers (can use `ui.state`)

#### `app`

App-wide storage, mount points and lifecycle hooks.

- storage:
    - `app.storage.tab`: stored in memory on the server, unique per tab
    - `app.storage.client`: stored in memory on the server, unique per client connected to a page
    - `app.storage.user`: stored in a file on the server, unique per browser
    - `app.storage.general`: stored in a file on the server, shared across the entire app
    - `app.storage.browser`: stored in the browser's local storage, unique per browser
- lifecycle hooks:
    - `app.on_connect()`: called when a client connects
    - `app.on_disconnect()`: called when a client disconnects
    - `app.on_startup()`: called when the app starts
    - `app.on_shutdown()`: called when the app shuts down
    - `app.on_exception()`: called when an exception occurs
- `app.shutdown()`: shut down the app
- static files:
    - `app.add_static_files()`, `app.add_static_file()`: serve static files
    - `app.add_media_files()`, `app.add_media_file()`: serve media files (supports streaming)
- `app.native`: configure the app when running in native mode

#### `html`

Pure HTML elements:

`a`,
`abbr`,
`acronym`,
`address`,
`area`,
`article`,
`aside`,
`audio`,
`b`,
`basefont`,
`bdi`,
`bdo`,
`big`,
`blockquote`,
`br`,
`button`,
`canvas`,
`caption`,
`cite`,
`code`,
`col`,
`colgroup`,
`data`,
`datalist`,
`dd`,
`del_`,
`details`,
`dfn`,
`dialog`,
`div`,
`dl`,
`dt`,
`em`,
`embed`,
`fieldset`,
`figcaption`,
`figure`,
`footer`,
`form`,
`h1`,
`header`,
`hgroup`,
`hr`,
`i`,
`iframe`,
`img`,
`input_`,
`ins`,
`kbd`,
`label`,
`legend`,
`li`,
`main`,
`map_`,
`mark`,
`menu`,
`meter`,
`nav`,
`object_`,
`ol`,
`optgroup`,
`option`,
`output`,
`p`,
`param`,
`picture`,
`pre`,
`progress`,
`q`,
`rp`,
`rt`,
`ruby`,
`s`,
`samp`,
`search`,
`section`,
`select`,
`small`,
`source`,
`span`,
`strong`,
`sub`,
`summary`,
`sup`,
`svg`,
`table`,
`tbody`,
`td`,
`template`,
`textarea`,
`tfoot`,
`th`,
`thead`,
`time`,
`tr`,
`track`,
`u`,
`ul`,
`var`,
`video`,
`wbr`,

#### `background_tasks`

Run async functions in the background.

- `create()`: create a background task
- `create_lazy()`: prevent two tasks with the same name from running at the same time

#### `run`

Run IO and CPU bound functions in separate threads and processes.

- `run.cpu_bound()`: run a CPU-bound function in a separate process
- `run.io_bound()`: run an IO-bound function in a separate thread

#### `observables`

Observable collections that notify observers when their contents change.

- `ObservableCollection`: base class
- `ObservableDict`: an observable dictionary
- `ObservableList`: an observable list
- `ObservableSet`: an observable set

#### `testing`

Write automated UI tests which run in a headless browser (slow) or fully simulated in Python (fast).

- `Screen` fixture: start a real (headless) browser to interact with your application
- `User` fixture: simulate user interaction on a Python level (fast)