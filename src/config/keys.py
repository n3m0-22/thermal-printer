class SettingsKeys:
    class Printer:
        MAC_ADDRESS = "printer.mac_address"
        DEVICE_NAME = "printer.device_name"
        WIDTH = "printer.width"
        RFCOMM_CHANNEL = "printer.rfcomm_channel"

    class Text:
        FONT_FAMILY = "text.font_family"
        FONT_SIZE = "text.font_size"
        ALIGNMENT = "text.alignment"
        BOLD = "text.bold"
        ITALIC = "text.italic"
        DARKNESS = "text.darkness"
        ADD_DATE = "text.add_date"
        DATE_FORMAT = "text.date_format"

    class Banner:
        FONT_FAMILY = "banner.font_family"
        FONT_SIZE = "banner.font_size"
        ALIGNMENT = "banner.alignment"
        BOLD = "banner.bold"
        ITALIC = "banner.italic"
        DARKNESS = "banner.darkness"
        ADD_DATE = "banner.add_date"
        DATE_FORMAT = "banner.date_format"

    class Image:
        BRIGHTNESS = "image.brightness"
        CONTRAST = "image.contrast"
        DITHER_MODE = "image.dither_mode"
        ROTATION = "image.rotation"
        INVERT = "image.invert"
        AUTO_RESIZE = "image.auto_resize"

    class Gui:
        WINDOW_WIDTH = "gui.window_width"
        WINDOW_HEIGHT = "gui.window_height"
        WINDOW_X = "gui.window_x"
        WINDOW_Y = "gui.window_y"
        APPEARANCE_MODE = "gui.appearance_mode"
        COLOR_THEME = "gui.color_theme"
        LAST_TAB = "gui.last_tab"
        GALLERY_THUMBNAIL_SIZE = "gui.gallery_thumbnail_size"
        PREVIEW_SCALE = "gui.preview_scale"

    class Timing:
        COMMAND_DELAY = "timing.command_delay"
        SCAN_TIMEOUT = "timing.scan_timeout"

    class Printing:
        FEED_LINES_BEFORE = "printing.feed_lines_before"
        FEED_LINES_AFTER = "printing.feed_lines_after"

    class Label:
        DARKNESS = "label.darkness"
        LAST_TEMPLATE_DIR = "label.last_template_dir"

    class Unicode:
        SHOW_FONT_SWITCH_POPUP = "unicode.show_font_switch_popup"
        PREFERRED_FONT = "unicode.preferred_font"
