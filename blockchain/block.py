from abc import ABC, abstractmethod # We want to make Block an abstract class; either a PoW or PoA block
import blockchain
from blockchain.util import sha256_2_string, encode_as_str
import time
import persistent
from blockchain.util import nonempty_intersection

class Block(ABC, persistent.Persistent):

    def __init__(self, height, transactions, parent_hash, is_genesis=False, include_merkle_root=True):
        """ Creates a block template (unsealed).

        Args:
            height (int): height of the block in the chain (# of blocks between block and genesis).
            transactions (:obj:`list` of :obj:`Transaction`): ordered list of transactions in the block.
            parent_hash (str): the hash of the parent block in the blockchain.
            is_genesis (bool, optional): True only if the block is a genesis block.

        Attributes:
            parent_hash (str): the hash of the parent block in blockchain.
            height (int): height of the block in the chain (# of blocks between block and genesis).
            transactions (:obj:`list` of :obj:`Transaction`): ordered list of transactions in the block.
            timestamp (int): Unix timestamp of the block.
            target (int): Target value for the block's seal to be valid (different for each seal mechanism)
            is_genesis (bool): True only if the block is a genesis block (first block in the chain).
            merkle (str): Merkle hash of the list of transactions in a block, uniquely identifying the list.
            seal_data (int): Seal data for block (in PoW this is the nonce satisfying the PoW puzzle; in PoA, the signature of the authority").
            hash (str): Hex-encoded SHA256^2 hash of the block header (self.header()).
        """
        self.parent_hash = parent_hash
        self.height = height
        self.transactions = transactions
        self.timestamp = int(time.time())
        self.target = self.calculate_appropriate_target()
        self.is_genesis = is_genesis
        
        if include_merkle_root:
            self.merkle = self.calculate_merkle_root()
        else:
            self.merkle = sha256_2_string("".join([str(x) for x in self.transactions]))

        self.seal_data = 0 # temporarily set seal_data to 0
        self.hash = self.calculate_hash() # keep track of hash for caching purposes

    def calculate_merkle_root(self):
        """ Gets the Merkle root hash for a given list of transactions.

        This method is incomplete!  Right now, it only hashes the
        transactions together, which does not enable the same type
        of lite client support a true Merkle hash would.

        Follow the description in the problem sheet to calculte the merkle root. 
        If there is no transaction, return SHA256(SHA256("")).
        If there is only one transaction, the merkle root is the transaction hash.
        For simplicity, when computing H(AB) = SHA256(SHA256(H(A) + H(B))), directly double-hash the hex string of H(A) concatenated with H(B).
        E.g., H(A) = 0x10, H(B) = 0xff, then H(AB) = SHA256(SHA256("10ff")).

        Returns:
            str: Merkle root hash of the list of transactions in a block, uniquely identifying the list.
        """

        hashed_tx = []

        for x in self.transactions:
            hashed_tx.append(sha256_2_string(str(x)))

        if len(hashed_tx) == 0: 
            return sha256_2_string("")
        elif len(hashed_tx) == 1:
            return hashed_tx[0]
        else: 
            # handling if merkle tree is uneven and greater than 1: https://bitcoin.stackexchange.com/questions/79364/are-number-of-transactions-in-merkle-tree-always-even
            if len(hashed_tx) % 2 != 0:
                hashed_tx.append(hashed_tx[-1])
            while len(hashed_tx) > 1:    
                holder = []                
                for i,k in zip(hashed_tx[0::2], hashed_tx[1::2]):
                    holder.append(sha256_2_string(i + k))
                hashed_tx = holder
            return hashed_tx[0]

    def unsealed_header(self):
        """ Computes the header string of a block (the component that is sealed by mining).

        Returns:
            str: String representation of the block header without the seal.
        """
        return encode_as_str([self.height, self.timestamp, self.target, self.parent_hash, self.is_genesis, self.merkle], sep='`')

    def header(self):
        """ Computes the full header string of a block after mining (includes the seal).

        Returns:
            str: String representation of the block header.
        """
        return encode_as_str([self.unsealed_header(), self.seal_data], sep='`')

    def calculate_hash(self):
        """ Get the SHA256^2 hash of the block header.

        Returns:
            str: Hex-encoded SHA256^2 hash of self.header()
        """
        return sha256_2_string(str(self.header()))

    def __repr__(self):
        """ Get a full representation of a block as string, for debugging purposes; includes all transactions.

        Returns:
            str: Full and unique representation of a block and its transactions.
        """
        return encode_as_str([self.header(), "!".join([str(tx) for tx in self.transactions])], sep="`")

    def set_seal_data(self, seal_data):
        """ Adds seal data to a block, recomputing the block's hash for its changed header representation.
        This method should never be called after a block is added to the blockchain!

        Args:
            seal_data (int): The seal data to set.
        """
        self.seal_data = seal_data
        self.hash = self.calculate_hash()

    def is_valid(self):
        """ Check whether block is fully valid according to block rules.

        Includes checking for no double spend, that all transactions are valid, that all header fields are correctly
        computed, etc.

        Returns:
            bool, str: True if block is valid, False otherwise plus an error or success message.
        """

        chain = blockchain.chain # This object of type Blockchain may be useful

        all_blocks = chain.get_chain_ending_with(self.hash)
        # print(all_blocks)
        # Placeholder for (1a)

        # (checks that apply to all blocks)
        # Check that Merkle root calculation is consistent with transactions in block (use the calculate_merkle_root function) [test_rejects_invalid_merkle]
        # On failure: return False, "Merkle root failed to match"

        if self.merkle != self.calculate_merkle_root():
            return False, "Merkle root failed to match"

        # Check that block.hash is correctly calculated [test_rejects_invalid_hash]
        # On failure: return False, "Hash failed to match"

        if self.hash != self.calculate_hash():
            return False, "Hash failed to match"

        # Check that there are at most 900 transactions in the block [test_rejects_too_many_txs]
        # On failure: return False, "Too many transactions"

        if len(self.transactions) > 900:
            return False, "Too many transactions"

        # (checks that apply to genesis block)
            # Check that height is 0 and parent_hash is "genesis" [test_invalid_genesis]
            # On failure: return False, "Invalid genesis"

        if self.is_genesis:
            if (self.height != 0 or self.parent_hash != "genesis"):
                return False, "Invalid genesis"

        else:
        # (checks that apply only to non-genesis blocks)

            # Check that parent exists (you may find chain.blocks helpful) [test_nonexistent_parent]
            # On failure: return False, "Nonexistent parent"
            if self.parent_hash not in chain.blocks:
                return False, "Nonexistent parent"
            else: 
                parent = chain.blocks[self.parent_hash]

                # Check that height is correct w.r.t. parent height [test_bad_height]
                # On failure: return False, "Invalid height"
                if self.height != parent.height + 1:
                    return False, "Invalid height"

                # Check that timestamp is non-decreasing [test_bad_timestamp]
                # On failure: return False, "Invalid timestamp"
                if self.timestamp < parent.timestamp:
                    return False, "Invalid timestamp"

            # Check that seal is correctly computed and satisfies "target" requirements; use the provided seal_is_valid method [test_bad_seal]
            # On failure: return False, "Invalid seal"
            if not self.seal_is_valid():
                return False, "Invalid seal"

            # Check that all transactions within are valid (use tx.is_valid) [test_malformed_txs]
            # On failure: return False, "Malformed transaction included"
            transactions = {}
            parent_chain = chain.get_chain_ending_with(self.parent_hash)
            for i, tx in enumerate(self.transactions): 
                h = tx.hash
                transactions[h] = i
                
            for tx in self.transactions: 
                if not tx.is_valid():
                    return False, "Malformed transaction included"

            # Check that for every transaction
                # the transaction has not already been included on a block on the same blockchain as this block [test_double_tx_inclusion_same_chain]
                # (or twice in this block; you will have to check this manually) [test_double_tx_inclusion_same_block]
                # (you may find chain.get_chain_ending_with and chain.blocks_containing_tx and util.nonempty_intersection useful)
                # On failure: return False, "Double transaction inclusion"

            if len(transactions) != len(self.transactions):
                return False, "Double transaction inclusion"

            for tx in self.transactions: 
                copy_list = chain.blocks_containing_tx.get(tx.hash, [])
                if nonempty_intersection(parent_chain, copy_list):
                    return False, "Double transaction inclusion"

                # for every input ref in the tx
                    # (you may find the string split method for parsing the input into its components)

                    # each input_ref is valid (aka corresponding transaction can be looked up in its holding transaction) [test_failed_input_lookup]
                    # (you may find chain.all_transactions useful here)
                    # On failure: return False, "Required output not found"
            block_inputs = []
            for tx in self.transactions:
                total_input = 0
                for r in tx.input_refs: 
                    split = r.split(':')
                    h = split[0]
                    i = int(split[1])

                    if h not in chain.all_transactions and h not in transactions:
                        return False, "Required output not found"

                    if h in chain.all_transactions: 
                        input_txs = chain.all_transactions[h]
                    else: 
                        input_txs = self.transactions[transactions[h]]

                    if len(input_txs.outputs) - 1 < i: 
                        return False, "Required output not found"

                    # every input was sent to the same user (would normally carry a signature from this user; we leave this out for simplicity) [test_user_consistency]
                    # On failure: return False, "User inconsistencies"
                    receiver = input_txs.outputs[i].receiver
                    senders = []

                    for user in tx.outputs:
                        senders.append(user.sender)

                    for sender in senders: 
                        if sender != receiver: 
                            return False, "User inconsistencies"

                    # no input_ref has been spent in a previous block on this chain [test_doublespent_input_same_chain]
                    # (or in this block; you will have to check this manually) [test_doublespent_input_same_block]
                    # (you may find nonempty_intersection and chain.blocks_spending_input helpful here)
                    # On failure: return False, "Double-spent input"

                    spend = chain.blocks_spending_input.get(r, [])
                    parent_chain = chain.get_chain_ending_with(self.parent_hash)
                    if len(spend) >= 1 and nonempty_intersection(parent_chain, spend):
                        return False, "Double-spent input"  
                    if r in block_inputs: 
                        return False, "Double-spent input" 
                    else:
                        block_inputs.append(r) 

                    # each input_ref points to a transaction on the same blockchain as this block [test_input_txs_on_chain]
                    # (or in this block; you will have to check this manually) [test_input_txs_in_block]
                    # (you may find chain.blocks_containing_tx.get and nonempty_intersection as above helpful)
                    # On failure: return False, "Input transaction not found"

                    blocks_with_transaction = chain.blocks_containing_tx.get(h, [])
                    if h not in transactions and not (nonempty_intersection(blocks_with_transaction, parent_chain)):
                        return False, "Input transaction not found"

                # for every output in the tx
                    # every output was sent from the same user (would normally carry a signature from this user; we leave this out for simplicity)
                    # (this MUST be the same user as the outputs are locked to above) [test_user_consistency]
                    # On failure: return False, "User inconsistencies"
                # the sum of the input values is at least the sum of the output values (no money created out of thin air) [test_no_money_creation]
                # On failure: return False, "Creating money"
            for tx in self.transactions:
                total_input = 0
                total_output = 0
                for output in tx.outputs:
                    total_output += output.amount

                for input_ref in tx.input_refs: 
                    split = input_ref.split(':')
                    h = split[0]
                    i = int(split[1])
                    input_transaction = chain.all_transactions[h] if h in chain.all_transactions else self.transactions[transactions[h]]
                total_input += input_transaction.outputs[i].amount
                if total_input < total_output: 
                    return False, "Creating money"
        return True, "All checks passed"


    # ( these just establish methods for subclasses to implement; no need to modify )
    @abstractmethod
    def get_weight(self):
        """ Should be implemented by subclasses; gives consensus weight of block. """
        pass

    @abstractmethod
    def calculate_appropriate_target(self):
        """ Should be implemented by subclasses; calculates correct target to use in block. """
        pass

    @abstractmethod
    def seal_is_valid(self):
        """ Should be implemented by subclasses; returns True iff the seal_data creates a valid seal on the block. """
        pass
