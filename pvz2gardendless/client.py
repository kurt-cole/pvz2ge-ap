"""Text client for PvZ2 Gardendless, with Universal Tracker support.

The GAME is played through the injected JS client (see build_pvzge_ap.py): it
opens its own websocket to the Archipelago server, sends its own checks and
receives its own items. This client plays nothing. It exists for the things a
browser tab cannot give you -- the chat log, !hint and the other server
commands, and above all Universal Tracker's tab, which is why it inherits from
UT's context when that apworld is installed.

Running it alongside the game is expected and supported: Archipelago allows more
than one connection to a slot, and both this and the JS client connect as
ordinary game clients.
"""

from __future__ import annotations

import asyncio
import sys

import Utils
from CommonClient import (
    ClientCommandProcessor,
    CommonContext,
    get_base_parser,
    gui_enabled,
    logger,
    server_loop,
)

# Universal Tracker, if the player has its apworld installed. Inheriting from
# its context is what puts the Tracker tab in this window; without it this is an
# ordinary text client and nothing else changes.
#
# The world's interpret_slot_data is the other half: which worlds this seed
# uses is a per-slot ROLL, so UT has to be handed the seed's real answers or the
# multiworld it rebuilds locally has different worlds in it than the server's.
try:
    from worlds.tracker.TrackerClient import TrackerGameContext as SuperContext

    TRACKER_LOADED = True
except ModuleNotFoundError:
    SuperContext = CommonContext
    TRACKER_LOADED = False

GAME_NAME = "PvZ2 Gardendless"


class PvZ2CommandProcessor(ClientCommandProcessor):
    def _cmd_worlds(self) -> bool:
        """List the worlds this seed contains, and the goal it wants."""
        self.ctx.print_seed_summary()
        return True


class PvZ2Context(SuperContext):
    game = GAME_NAME
    command_processor = PvZ2CommandProcessor
    # The same handling the injected client asks for. Two clients on one slot
    # both receive the full item stream, which is what makes this a companion
    # window rather than a second player.
    items_handling = 0b111
    # Universal Tracker's context adds a "Tracker" tag of its own; this is a
    # game client and must not claim to be a tracker to the server.
    tags = {"AP"}

    def __init__(self, server_address: str | None, password: str | None) -> None:
        super().__init__(server_address, password)
        self.slot_data: dict = {}

    async def server_auth(self, password_requested: bool = False) -> None:
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict) -> None:
        # UT's context reads Connected itself to kick off its re-generation, so
        # this has to run first and unconditionally.
        super().on_package(cmd, args)
        if cmd == "Connected":
            self.slot_data = args.get("slot_data", {}) or {}
            self.print_seed_summary()
            if not TRACKER_LOADED:
                logger.info(
                    "Universal Tracker is not installed, so this window has no "
                    "Tracker tab. Everything else works without it."
                )

    def print_seed_summary(self) -> None:
        """What this seed is, in three lines. Cheap orientation on connect."""
        if not self.slot_data:
            logger.info("Not connected to a PvZ2 Gardendless slot yet.")
            return
        worlds = self.slot_data.get("enabled_worlds") or []
        goal_type = self.slot_data.get("goal_type", "?")
        required = self.slot_data.get("worlds_required", "?")
        logger.info(f"Worlds in this seed ({len(worlds)}): {', '.join(worlds)}")
        logger.info(f"Goal: complete {required} of them ({goal_type}).")
        if self.slot_data.get("shopsanity"):
            logger.info("Shopsanity is on: store purchases are checks.")

    def make_gui(self):
        """Name the window for this game rather than "Archipelago Text Client".

        super() rather than kvui.GameManager on purpose: with Universal Tracker
        installed this inherits its UI, which is what carries the Tracker tab.
        """
        ui = super().make_gui()
        ui.base_title = f"Archipelago {GAME_NAME} Client"
        return ui


async def main(args) -> None:
    ctx = PvZ2Context(args.connect, args.password)
    ctx.server_task = asyncio.create_task(server_loop(ctx), name="ServerLoop")

    # Universal Tracker builds its own copy of the multiworld before the UI
    # comes up; without this its tab exists but has nothing in it.
    if TRACKER_LOADED:
        ctx.run_generator()

    if gui_enabled:
        ctx.run_gui()
    ctx.run_cli()

    await ctx.exit_event.wait()
    await ctx.shutdown()


def launch(*args: str) -> None:
    parser = get_base_parser(description="PvZ2 Gardendless Archipelago client")
    parser.add_argument("url", nargs="?", help="Archipelago connection URI")
    parsed = parser.parse_args(args)

    if parsed.url:
        # parse_uri fills connect/password in from an archipelago:// link. Not
        # present in every AP build, and an unparsed URL is better than a crash.
        parsed = (Utils.parse_uri(parsed, parser)
                  if hasattr(Utils, "parse_uri") else parsed)

    Utils.init_logging("PvZ2GardendlessClient", exception_logger="Client")
    asyncio.run(main(parsed))


if __name__ == "__main__":
    launch(*sys.argv[1:])
