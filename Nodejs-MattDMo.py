import os
import subprocess
import sublime
import sublime_plugin

from .lib.command_thread import CommandThread

PLUGIN_DIRECTORY = os.getcwd().replace(os.path.normpath(os.path.join(os.getcwd(), '..', '..')) + os.path.sep, '').replace(os.path.sep, '/')
PLUGIN_PATH = os.getcwd().replace(os.path.join(os.getcwd(), '..', '..') + os.path.sep, '').replace(os.path.sep, '/')

settings = sublime.load_settings("Nodejs-MattDMo.sublime-settings")
NODE_COMMAND = settings.get("node_command", "node")
NPM_COMMAND = settings.get("npm_command", "npm")


def open_url(url):
    sublime.active_window().run_command('open_url', {"url": url})

def view_contents(view):
    region = sublime.Region(0, view.size())
    return view.substr(region)

def plugin_file(name):
    return os.path.join(PLUGIN_DIRECTORY, name)


class NodeCommand(sublime_plugin.TextCommand):
    def run_command(self, command, callback=None, show_status=True, filter_empty_args=True, **kwargs):
        print("Command is:", command)
        print("NODE_COMMAND is:", NODE_COMMAND)
        print("NPM_COMMAND is:", NPM_COMMAND)

        if filter_empty_args:
            command = [arg for arg in command if arg]
        if 'working_dir' not in kwargs:
            kwargs['working_dir'] = self.get_working_dir()
        s = sublime.load_settings("Nodejs-MattDMo.sublime-settings")
        if s.get('save_first') and self.active_view() and self.active_view().is_dirty():
            self.active_view().run_command('save')
        if command[0] == 'node' and NODE_COMMAND:
            command[0] = NODE_COMMAND
            if 'env' not in kwargs:
                kwargs['env'] = {"NODE_PATH": s.get('node_path')}
        if command[0] == 'npm' and NPM_COMMAND:
            command[0] = NPM_COMMAND
        if not callback:
            callback = self.generic_done

        print("Just before calling CommandThread, command is:", command)
        # command = " ".join(command)
        # print("Now, command is", command)
        thread = CommandThread(command, callback, **kwargs)
        print("Just called CommandThread")
        thread.start()

        if show_status:
            message = kwargs.get('status_message', False) or ' '.join(command)
            sublime.status_message(message)

    def generic_done(self, result):
        if not result.strip():
            return
        self.panel(result)

    def _output_to_view(self, output_file, output, clear=False, syntax="Packages/JavaScriptNext - ES6 Syntax/JavaScriptNext.tmLanguage"):
        output_file.set_syntax_file(syntax)
        edit = output_file.begin_edit()
        if clear:
            region = sublime.Region(0, self.output_view.size())
            output_file.erase(edit, region)
        output_file.insert(edit, 0, output)
        output_file.end_edit(edit)

    def scratch(self, output, title=False, **kwargs):
        scratch_file = self.get_window().new_file()
        if title:
            scratch_file.set_name(title)
        scratch_file.set_scratch(True)
        self._output_to_view(scratch_file, output, **kwargs)
        scratch_file.set_read_only(True)
        return scratch_file

    def panel(self, output, **kwargs):
        if not hasattr(self, 'output_view'):
            self.output_view = self.get_window().create_output_panel("node")
        self.output_view.set_read_only(False)
        self._output_to_view(self.output_view, output, clear=True, **kwargs)
        self.output_view.set_read_only(True)
        self.get_window().run_command("show_panel", {"panel": "output.node"})

    def quick_panel(self, *args, **kwargs):
        self.get_window().show_quick_panel(*args, **kwargs)

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()


class NodeWindowCommand(NodeCommand, sublime_plugin.WindowCommand):
    def active_view(self):
        return self.window.active_view()

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()

    # def is_enabled(self):
    #     if self._active_file_name() or len(self.window.folders()) == 1:
    #         return True if os.path.realpath(self.get_working_dir()) else False
    #     return True

    def get_file_name(self):
        return ''

    # If there is a file in the active view use that file's directory to
    # search for the Git root. Otherwise, use the only folder that is
    # open.
    def get_working_dir(self):
        file_name = self._active_file_name()
        if file_name:
            return os.path.dirname(file_name)
        else:
            return self.window.folders()[0]

    def get_window(self):
        return self.window


# A base for all git commands that work with the file in the active view
class NodeTextCommand(NodeCommand, sublime_plugin.TextCommand):
    def active_view(self):
        return self.view

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()

    # def is_enabled(self):
    #     # First, is this actually a file on the file system?
    #     if self._active_file_name() or len(self.window.folders()) == 1:
    #         return True if os.path.realpath(self.get_working_dir()) else False
    #     return True

    def get_file_name(self):
        return os.path.basename(self.view.file_name())

    def get_working_dir(self):
        return os.path.dirname(self.view.file_name())

    def get_window(self):
        # Fun discovery: if you switch tabs while a command is working,
        # self.view.window() is None. (Admittedly this is a consequence
        # of my deciding to do async command processing... but, hey,
        # got to live with that now.)
        # I did try tracking the window used at the start of the command
        # and using it instead of view.window() later, but that results
        # panels on a non-visible window, which is especially useless in
        # the case of the quick panel.
        # So, this is not necessarily ideal, but it does work.
        return self.view.window() or sublime.active_window()

# Commands to run


# Command to build docs
class NodeBuilddocsCommand(NodeTextCommand):
    def run(self, edit):
        doc_builder = os.path.join(PLUGIN_PATH, 'tools/default_build.js')
        command = ['NODE_COMMAND', doc_builder]
        self.run_command(command, self.command_done)

    def command_done(self, result):
        s = sublime.load_settings("Nodejs-MattDMo.sublime-settings")
        if s.get('output_to_new_tab'):
            self.scratch(result, title="Node Output", syntax="Packages/JavaScriptNext - ES6 Syntax/JavaScriptNext.tmLanguage")
        else:
            self.panel(result)

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()

# Command to Run node
class NodeRunCommand(NodeTextCommand):
    def run(self, edit):
        command = """kill -9 `ps -ef | grep node | grep -v grep | awk '{print $2}'`"""
        os.system(command)
        command = [NODE_COMMAND, self.view.file_name()]
        self.run_command(command, self.command_done)

    def command_done(self, result):
        s = sublime.load_settings("Nodejs-MattDMo.sublime-settings")
        if s.get('output_to_new_tab'):
            self.scratch(result, title="Node Output", syntax="Packages/JavaScriptNext - ES6 Syntax/JavaScriptNext.tmLanguage")
        else:
            self.panel(result)

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()

# Command to run node with debug
class NodeDrunCommand(NodeTextCommand):
    def run(self, edit):
        command = """kill -9 `ps -ef | grep node | grep -v grep | awk '{print $2}'`"""
        os.system(command)
        command = [NODE_COMMAND, 'debug', self.view.file_name()]
        self.run_command(command, self.command_done)

    def command_done(self, result):
        s = sublime.load_settings("Nodejs-MattDMo.sublime-settings")
        if s.get('output_to_new_tab'):
            self.scratch(result, title="Node Output", syntax="Packages/JavaScriptNext - ES6 Syntax/JavaScriptNext.tmLanguage")
        else:
            self.panel(result)

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()

# Command to run node with arguments
class NodeRunArgumentsCommand(NodeTextCommand):
    def run(self, edit):
        self.get_window().show_input_panel("Arguments", "", self.on_input, None, None)

    def on_input(self, message):
        command = message.split()
        command.insert(0, self.view.file_name())
        command.insert(0, NODE_COMMAND)
        self.run_command(command, self.command_done)

    def command_done(self, result):
        self.scratch(result, title="Node Output", syntax="Packages/JavaScriptNext - ES6 Syntax/JavaScriptNext.tmLanguage")

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()


# Command to run node with debug and arguments
class NodeDrunArgumentsCommand(NodeTextCommand):
    def run(self, edit):
        self.get_window().show_input_panel("Arguments", "", self.on_input, None, None)

    def on_input(self, message):
        command = message.split()
        command.insert(0, self.view.file_name())
        command.insert(0, 'debug')
        command.insert(0, NODE_COMMAND)
        self.run_command(command, self.command_done)

    def command_done(self, result):
        s = sublime.load_settings("Nodejs-MattDMo.sublime-settings")
        if s.get('output_to_new_tab'):
            self.scratch(result, title="Node Output", syntax="Packages/JavaScriptNext - ES6 Syntax/JavaScriptNext.tmLanguage")
        else:
            self.panel(result)

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()


class NodeNpmCommand(NodeTextCommand):
    def run(self, edit):
        self.get_window().show_input_panel("Arguments", "", self.on_input, None, None)

    def on_input(self, message):
        command = message.split()
        command.insert(0, "npm")
        self.run_command(command, self.command_done)

    def command_done(self, result):
        s = sublime.load_settings("Nodejs-MattDMo.sublime-settings")
        if s.get('output_to_new_tab'):
            self.scratch(result, title="Node Output", syntax="Packages/Text/Plain text.tmLanguage")
        else:
            self.panel(result)

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()


class NodeNpmInstallCommand(NodeTextCommand):
    def run(self, edit):
        self.run_command([NPM_COMMAND, 'install'], self.command_done)

    def command_done(self, result):
        s = sublime.load_settings("Nodejs-MattDMo.sublime-settings")
        if s.get('output_to_new_tab'):
            self.scratch(result, title="Node Output", syntax="Packages/Text/Plain text.tmLanguage")
        else:
            self.panel(result)

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()


class NodeNpmUninstallCommand(NodeTextCommand):
    def run(self, edit):
        self.get_window().show_input_panel("Package", "", self.on_input, None, None)

    def on_input(self, message):
        command = message.split()
        command.insert(0, "npm")
        command.insert(1, "uninstall")
        self.run_command(command, self.command_done)

    def command_done(self, result):
        s = sublime.load_settings("Nodejs-MattDMo.sublime-settings")
        if s.get('output_to_new_tab'):
            self.scratch(result, title="Node Output", syntax="Packages/Text/Plain text.tmLanguage")
        else:
            self.panel(result)

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()


class NodeNpmSearchCommand(NodeTextCommand):
    def run(self, edit):
        self.get_window().show_input_panel("Term", "", self.on_input, None, None)

    def on_input(self, message):
        command = message.split()
        command.insert(0, "npm")
        command.insert(1, "search")
        self.run_command(command, self.command_done)

    def command_done(self, result):
        s = sublime.load_settings("Nodejs-MattDMo.sublime-settings")
        if s.get('output_to_new_tab'):
            self.scratch(result, title="Node Output", syntax="Packages/Text/Plain text.tmLanguage")
        else:
            self.panel(result)

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()


class NodeNpmPublishCommand(NodeTextCommand):
    def run(self, edit):
        self.run_command([NPM_COMMAND, 'publish'], self.command_done)

    def command_done(self, result):
        s = sublime.load_settings("Nodejs-MattDMo.sublime-settings")
        if s.get('output_to_new_tab'):
            self.scratch(result, title="Node Output", syntax="Packages/Text/Plain text.tmLanguage")
        else:
            self.panel(result)

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()


class NodeNpmUpdateCommand(NodeTextCommand):
    def run(self, edit):
        self.run_command([NPM_COMMAND, 'update'], self.command_done)

    def command_done(self, result):
        s = sublime.load_settings("Nodejs-MattDMo.sublime-settings")
        if s.get('output_to_new_tab'):
            self.scratch(result, title="Node Output", syntax="Packages/Text/Plain text.tmLanguage")
        else:
            self.panel(result)

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()


class NodeNpmListCommand(NodeTextCommand):
    def run(self, edit):
        self.run_command([NPM_COMMAND, 'ls'], self.command_done)

    def command_done(self, result):
        s = sublime.load_settings("Nodejs-MattDMo.sublime-settings")
        if s.get('output_to_new_tab'):
            self.scratch(result, title="Node Output", syntax="Packages/Text/Plain text.tmLanguage")
        else:
            self.panel(result)

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()


class NodeUglifyCommand(NodeTextCommand):
    def run(self, edit):
        uglify = os.path.join(PLUGIN_PATH, 'tools/uglify_js.js')
        command = [NODE_COMMAND, uglify, '-i', self.view.file_name()]
        self.run_command(command, self.command_done)

    def command_done(self, result):
        s = sublime.load_settings("Nodejs-MattDMo.sublime-settings")
        if s.get('output_to_new_tab'):
            self.scratch(result, title="Node Output", syntax="Packages/JavaScriptNext - ES6 Syntax/JavaScriptNext.tmLanguage")
        else:
            self.panel(result)

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()
