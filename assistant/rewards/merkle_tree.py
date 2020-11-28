import json
import os
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from functools import partial, wraps
from itertools import zip_longest
from pathlib import Path
from dotmap import DotMap
import toml
from brownie import *
from eth_abi import decode_single, encode_single
from eth_abi.packed import encode_abi_packed
from eth_utils import encode_hex
from toolz import valfilter, valmap
from tqdm import tqdm, trange
from click import secho
from helpers.constants import *
import hashlib
from rich.console import Console

console = Console()

"""
Convert merkle_tree
"""


class MerkleTree:
    def __init__(self, elements):
        self.elements = sorted(set(web3.keccak(hexstr=el) for el in elements))
        self.layers = MerkleTree.get_layers(self.elements)

        console.log(self.elements, self.layers)

    @property
    def root(self):
        return self.layers[-1][0]

    def get_proof(self, el):
        el = web3.keccak(hexstr=el)
        idx = self.elements.index(el)
        proof = []
        for layer in self.layers:
            pair_idx = idx + 1 if idx % 2 == 0 else idx - 1
            if pair_idx < len(layer):
                proof.append(encode_hex(layer[pair_idx]))
            idx //= 2
        return proof

    @staticmethod
    def get_layers(elements):
        layers = [elements]
        while len(layers[-1]) > 1:
            layers.append(MerkleTree.get_next_layer(layers[-1]))
        return layers

    @staticmethod
    def get_next_layer(elements):
        return [
            MerkleTree.combined_hash(a, b)
            for a, b in zip_longest(elements[::2], elements[1::2])
        ]

    @staticmethod
    def combined_hash(a, b):
        if a is None:
            return b
        if b is None:
            return a
        return web3.keccak(b"".join(sorted([a, b])))


def rewards_to_merkle_tree(rewards):
    (nodes, encodedNodes) = rewards.to_merkle_format()
    console.log(nodes, encodedNodes)

    # For each user, encode their data into a node

    # Put the nodes into a tree

    # elements = [(index, account, amount) for index, (account, amount) in enumerate(rewards.items())]
    # nodes = [encode_hex(encode_abi_packed(['uint', 'address', 'uint'], el)) for el in elements]
    """
    'claims': {
            user: {'index': index, 'amount': hex(amount), 'proof': tree.get_proof(nodes[index])}
            for index, user, amount in elements
        },
    """
    tree = MerkleTree(encodedNodes)
    distribution = {
        "merkleRoot": encode_hex(tree.root),
        "cycle": nodes[0]["cycle"],
        "tokenTotals": rewards.totals.toDict(),
        "claims": {},
    }

    for node in nodes:
        console.log(node)
        distribution["claims"][node["user"]] = {
            "index": hex(node["index"]),
            "user": node["user"],
            "cycle": hex(node["cycle"]),
            "tokens": node["tokens"],
            "cumulativeAmounts": node["cumulativeAmounts"],
            "proof": tree.get_proof(encodedNodes[node["index"]]),
        }

    print(f"merkle root: {encode_hex(tree.root)}")

    # Print to file with content hash
    # hash(distribution)

    console.log(distribution)

    return distribution