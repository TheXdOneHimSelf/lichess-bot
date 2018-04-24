import os
import chess
import chess.xboard
import chess.uci

def create_engine(config, board):
    # print("Loading Engine!")
    cfg = config["engine"]
    engine_path = os.path.join(cfg["dir"], cfg["name"])
    weights = os.path.join(cfg["dir"], cfg["weights"]) if "weights" in cfg else None
    threads = cfg.get("threads")
    tempdecay = cfg.get("tempdecay")

    # TODO: ucioptions should probably be a part of the engine subconfig
    ucioptions = config.get("ucioptions")
    engine_type = cfg.get("protocol")
    commands = [engine_path]
    if weights:
        commands.append("-w")
        commands.append(weights)
    if threads:
        commands.append("-t")
        commands.append(str(threads))
    if tempdecay:
        commands.append("-d")
        commands.append(str(tempdecay))

    if engine_type == "xboard":
        return XBoardEngine(board, commands)

    return UCIEngine(board, commands, ucioptions)


class EngineWrapper:

    def __init__(self, board, commands):
        pass

    def pre_game(self, game):
        pass

    def first_search(self, movetime):
        pass

    def search(self, board, wtime, btime, winc, binc):
        pass

    def print_stats(self):
        pass

    def name(self):
        return self.engine.name

    def quit(self):
        self.engine.quit()

    def get_handler_stats(self, info, stats, to_print=False):
        stats_info = []
        for stat in stats:
            if stat in info:
                str = "{}: {}".format(stat, info[stat])
                if stat == "score":
                    for k,v in info[stat].items():
                        str = "score: {}".format(v.cp)
                        feval = 0.322978*math.atan(0.0034402*v.cp) + 0.5
                stats_info.append(str)
                if to_print:
                    print("    {}".format(str))
            if stat == "exp":
                str = "exp: {:0.1%}".format(feval)
                stats_info.append(str)
                if to_print:
                    print("    {}".format(str))

        return stats_info


class XBoardEngine(EngineWrapper):

    def __init__(self, board, commands):
        commands = commands[0] if len(commands) == 1 else commands
        self.engine = chess.xboard.popen_engine(commands)

        self.engine.xboard()

        if board.chess960:
            self.engine.send_variant("fischerandom")
        elif type(board).uci_variant != "chess":
            self.engine.send_variant(type(board).uci_variant)

        self.engine.setboard(board)

        post_handler = chess.xboard.PostHandler()
        self.engine.post_handlers.append(post_handler)

    def pre_game(self, game):
        minutes = game.clock_initial / 1000 / 60
        seconds = game.clock_initial / 1000 % 60
        inc = game.clock_increment / 1000
        self.engine.level(0, minutes, seconds, inc)

    def first_search(self, board, movetime):
        self.engine.setboard(board)
        self.engine.st(movetime / 1000)
        return self.engine.go()

    def search(self, board, wtime, btime, winc, binc):
        self.engine.setboard(board)
        if board.turn == chess.WHITE:
            self.engine.time(wtime / 10)
            self.engine.otim(btime / 10)
        else:
            self.engine.time(btime / 10)
            self.engine.otim(wtime / 10)
        return self.engine.go()

    def print_stats(self):
        self.print_handler_stats(self.engine.post_handlers[0].post, ["depth", "nodes", "score"])

class UCIEngine(EngineWrapper):

    def __init__(self, board, commands, options):
        commands = commands[0] if len(commands) == 1 else commands
        self.engine = chess.uci.popen_engine(commands)

        self.engine.uci()

        if options:
            self.engine.setoption(options)

        self.engine.setoption({"UCI_Variant": type(board).uci_variant})
        self.engine.position(board)

        info_handler = chess.uci.InfoHandler()
        self.engine.info_handlers.append(info_handler)

    def pre_game(self, game):
        if game.speed == "ultraBullet":
            self.engine.setoption({"slowmover": "50"})
        if game.speed == "bullet":
            self.engine.setoption({"slowmover": "80"})
        if game.speed == "blitz":
            self.engine.setoption({"slowmover": "100"})
        if game.speed == "rapid":
            self.engine.setoption({"slowmover": "125"})
        if game.speed == "classical":
            self.engine.setoption({"slowmover": "125"}) #optimal

    def first_search(self, board, movetime):
        self.engine.setoption({"UCI_Variant": type(board).uci_variant})
        self.engine.position(board)
        best_move, _ = self.engine.go(movetime=movetime)
        return best_move

    def search(self, board, wtime, btime, winc, binc):
        self.engine.setoption({"UCI_Variant": type(board).uci_variant})
        self.engine.position(board)
        best_move, _ = self.engine.go(
            wtime=wtime,
            btime=btime,
            winc=winc,
            binc=binc
        )
        return best_move

    def get_stats(self, to_print):
        return self.get_handler_stats(self.engine.info_handlers[0].info, ["depth", "nps", "nodes", "score", "exp"], to_print)
