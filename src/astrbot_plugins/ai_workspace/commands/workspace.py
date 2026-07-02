from __future__ import annotations

from astrbot.api.event import AstrMessageEvent, filter

from ..utils import command_args, file_result, parse_out, text_result


class WorkspaceCommands:
    @filter.command("ask")
    async def ask(self, event: AstrMessageEvent):
        args = command_args(event.message_str, "ask")
        if len(args) >= 3:
            source_type, category = args[0], args[1]
            question = " ".join(args[2:])
        else:
            source_type = None
            category = None
            question = " ".join(args)
        data = self.workspace_client.post(
            "/ask",
            {"question": question, "source_type": source_type, "category": category},
            timeout=180,
        )
        yield event.plain_result(text_result(data))

    @filter.command("file")
    async def file(self, event: AstrMessageEvent):
        args, output_dir = parse_out(command_args(event.message_str, "file"))
        if len(args) < 3:
            yield event.plain_result("Usage: /file <source_type> <category> <filename> [--out output_dir]")
            return
        source_type, category, filename = args[0], args[1], args[2]
        data = self.workspace_client.post(
            "/file",
            {
                "source_type": source_type,
                "category": category,
                "filename": filename,
                "output_dir": output_dir,
            },
            timeout=180,
        )
        yield event.plain_result(file_result(data))

    @filter.command("analyze_file")
    async def analyze_file(self, event: AstrMessageEvent):
        args, output_dir = parse_out(command_args(event.message_str, "analyze_file"))
        if len(args) < 3:
            yield event.plain_result("Usage: /analyze_file <source_type> <category> <filename> [--out output_dir]")
            return
        source_type, category, filename = args[0], args[1], args[2]
        data = self.workspace_client.post(
            "/file",
            {
                "source_type": source_type,
                "category": category,
                "filename": filename,
                "output_dir": output_dir,
            },
            timeout=180,
        )
        yield event.plain_result(file_result(data))

    @filter.command("analyze_pdf")
    async def analyze_pdf(self, event: AstrMessageEvent):
        args, output_dir = parse_out(command_args(event.message_str, "analyze_pdf"))
        if len(args) < 2:
            yield event.plain_result("Usage: /analyze_pdf <category> <filename> [--out output_dir]")
            return
        category, filename = args[0], args[1]
        data = self.workspace_client.post(
            "/file",
            {
                "source_type": "pdf",
                "category": category,
                "filename": filename,
                "output_dir": output_dir,
            },
            timeout=180,
        )
        yield event.plain_result(file_result(data))

    @filter.command("web")
    async def web(self, event: AstrMessageEvent):
        args, output_dir = parse_out(command_args(event.message_str, "web"))
        if len(args) < 2:
            yield event.plain_result("Usage: /web <category> <url> [--out output_dir]")
            return
        data = self.workspace_client.post(
            "/web",
            {"category": args[0], "url": args[1], "output_dir": output_dir},
            timeout=180,
        )
        yield event.plain_result(text_result(data))

    @filter.command("video")
    async def video(self, event: AstrMessageEvent):
        args, output_dir = parse_out(command_args(event.message_str, "video"))
        if len(args) < 2:
            yield event.plain_result("Usage: /video <category> <url> [--out output_dir]")
            return
        data = self.workspace_client.post(
            "/video",
            {"category": args[0], "url": args[1], "output_dir": output_dir},
            timeout=180,
        )
        yield event.plain_result(text_result(data))

    @filter.command("transcribe")
    async def transcribe(self, event: AstrMessageEvent):
        args, output_dir = parse_out(command_args(event.message_str, "transcribe"))
        if len(args) < 2:
            yield event.plain_result("Usage: /transcribe <category> <url_or_file> [--out output_dir]")
            return
        data = self.workspace_client.post(
            "/transcribe",
            {"category": args[0], "url_or_file": args[1], "output_dir": output_dir},
            timeout=180,
        )
        yield event.plain_result(text_result(data))
