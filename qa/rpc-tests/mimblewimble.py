#!/usr/bin/env python3
# Copyright (c) 2014-2016 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""mimblewimble RPCs QA test.

# Tests the following RPCs:
#    - mergemwtransactions
"""

from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import *

class MimblewimbleTest(BitcoinTestFramework):

    def __init__(self):
        super().__init__()
        self.setup_clean_chain = True
        self.num_nodes = 3


    def setup_network(self, split=False):
        self.nodes = start_nodes(self.num_nodes, self.options.tmpdir)
        connect_nodes_bi(self.nodes,0,1)
        connect_nodes_bi(self.nodes,1,2)
        connect_nodes_bi(self.nodes,0,2)
        self.is_network_split=False
        self.sync_all()

    def run_test(self):

        # generate initial coins and make sure they are mature
        self.nodes[0].generate(1)
        self.sync_all()
        self.nodes[1].generate(101)
        self.sync_all()

        # set all OP_TRUE genesis outputs to single node
        self.nodes[0].sendtoaddress(self.nodes[0].getnewaddress(), 21000000, "", "", True)
        self.nodes[0].generate(101)
        self.sync_all()

        assert_equal(self.nodes[0].getbalance("", 0, False, "bitcoin"), 21000000)
        assert_equal(self.nodes[1].getbalance("", 0, False, "bitcoin"), 0)
        assert_equal(self.nodes[2].getbalance("", 0, False, "bitcoin"), 0)

        # send some coins to prepare for command tests
        txid0 = self.nodes[0].sendtoaddress(self.nodes[2].getnewaddress(), 1.5)
        #txid1 = self.nodes[0].sendtoaddress(self.nodes[2].getnewaddress(), 3.5)
        txid2 = self.nodes[0].sendtoaddress(self.nodes[1].getnewaddress(), 10.0)
        self.sync_all()
        self.nodes[0].generate(101)
        self.sync_all()

        # current node values:
        # node 0: 20999985 BTC
        # node 1: 10 BTC
        # node 2: 5 BTC

        dectx0 = self.nodes[0].gettransaction(txid0)
        rawtx0 = self.nodes[0].decoderawtransaction(dectx0['hex'])

        # find proper outpoint because of non-determinism
        vout = False
        for outpoint in rawtx0['vout']:
            if outpoint['scriptPubKey']['type'] == 'fee':
                continue
            if outpoint['value-maximum'] == Decimal('42.94967296'):
                vout = outpoint
        
        node1address = self.nodes[0].validateaddress(self.nodes[1].getnewaddress())['unconfidential']
        node2change = self.nodes[0].validateaddress(self.nodes[2].getnewaddress())['unconfidential']
        print(self.nodes[0].gettransaction(txid0)["amount"])
        print("PRINTING VOUT BELOW")
        print(vout['n'])
        print(vout)
        print("")
        # build first incomplete tx, node 2 sending to node 1
        inputs = [{"txid": txid0, "vout": vout['n'], "amount": Decimal('1.5')}]
        outputs = {"fee": Decimal('0.05'), node2change: Decimal('0.4')}
        rawtx1 = self.nodes[2].createrawtransaction(inputs, outputs, 0, None, True)

        # build second incomplete tx, node 1 receiving from node 2
        inputs = []
        outputs = {"fee": Decimal('0.05'), node1address: Decimal('1.0')}
        rawtx2 = self.nodes[1].createrawtransaction(inputs, outputs, 0, None, True)

        merged = self.nodes[0].mergemwtransactions([rawtx1, rawtx2])
        jsonmerged = self.nodes[1].decoderawtransaction(merged)

        for thing in jsonmerged['vin']:
            print(thing)
            print("")
        print("--------------------------------------------------")
        for thing in jsonmerged['vout']:
            print(thing)
            print("")

        merged = self.nodes[2].blindrawtransaction(merged)
        merged = self.nodes[2].signrawtransaction(merged)['hex']
        print(self.nodes[2].sendrawtransaction(merged))


if __name__ == '__main__':
    MimblewimbleTest().main()
