from mctslib import MCTS
from ale_py import ALEInterface
from argparse import ArgumentParser
from tqdm import tqdm
import numpy as np
import os
import os.path
import random

class ALENode:
    def __init__(self, ram, parent, score, action, is_terminal):
        self.ram = ram
        self.parent = parent
        self.evaluation = score
        self.action = action
        self.is_terminal = is_terminal


    @classmethod
    def setup_interface(cls, rom_path, frame_skip):
        interface = ALEInterface()
        interface.setInt("frame_skip", frame_skip)
        interface.setFloat("repeat_action_probability", 0)
        interface.loadROM(rom_path)
        cls.interface = interface

    @classmethod
    def root(cls):
        ram = cls.interface.getRAM()
        parent = None
        score = 0
        action = 0 # attribute start of game to NOOP
        is_terminal = cls.interface.game_over()

        return cls(ram, parent, score, action, is_terminal)

    @classmethod 
    def from_parent(cls, parent, action):
        parent.sync()
        inc_reward = cls.interface.act(action)

        new_ram = cls.interface.getRAM()
        is_terminal = cls.interface.game_over()

        return cls(new_ram, parent, parent.evaluation + inc_reward, action, is_terminal)

    def sync(self):
        for i, b in enumerate(self.ram):
            self.interface.setRAM(i, b)
    
    def find_children(self):
        actions = self.interface.getMinimalActionSet()

        return [ALENode.from_parent(self, a) for a in actions]

    def random_child(self):
        return random.choice(self.find_children())

    def get_history(self):
        history = []
        node = self
        while node.parent:
            history.append(node)
            node = node.parent
        
        return list(reversed(history))

    def make_video(self, png_dir, video_path):
        history = self.get_history()

        for i, n in enumerate(history[:-1]):
            n.sync()
            self.interface.act(history[i+1].action)
            fname = f"frame_{i}.png"
            self.interface.saveScreenPNG(f"{os.path.join(png_dir, fname)}")

        os.system(f"ffmpeg -framerate 60 -start_number 0 -i {png_dir}/frame_%d.png -pix_fmt yuv420p {video_path}")
        # os.system(f"rm -rf {png_dir}")

    def __hash__(self):
        return hash(self.ram.tobytes())
    
    def __eq__(self, other):
        return np.array_equal(self.ram, other.ram)

    def __repr__(self):
        return f"{self.__class__.__name__}<{self.evaluation=}, {self.action=}>"

if __name__ == "__main__":
    parser = ArgumentParser(description="Run MCTS on ALE")

    args = [
        ("rom_path", {"type": str}),
        ("--exploration_weight", {"type": float, "required": True}),
        ("--cpu_time", {"type": float, "required": True}),
        ("--rollout_depth", {"type": int, "required": True}),
        ("--frame_skip", {"type": int, "required": True}),
        ("--turn_limit", {"type": int, "required": True}),
        ("--png_dir", {"type": str, "required": True}),
        ("--video_path", {"type": str, "required": True}),
    ]


    for name, opts in args:
        parser.add_argument(name, **opts)
    
    args = parser.parse_args()

    ALENode.setup_interface(args.rom_path, args.frame_skip)

    mcts = MCTS(ALENode.root(), hashable=True)

    for i in tqdm(range(args.turn_limit)):
        node = mcts.move(rollout_depth=args.rollout_depth, cpu_time=args.cpu_time)
    print(node)
    node.make_video(args.png_dir, args.video_path)


