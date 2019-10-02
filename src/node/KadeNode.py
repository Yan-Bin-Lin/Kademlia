'''
Created on 2019年9月1日

@author: danny
'''
import pickle
from pathlib import Path
import time

from .KBucket import KBucket
from .NodeData import NodeData
from .RouteTable import RouteTable
from ..crypto.RSASign import RSA
from ..network.connect import Connect
from ..util.hash import *
from ..handler.respond import *
from ..handler.ask import Ask#, Reject

import logging
logger = logging.getLogger( 'loglog' )
# a single kade node
class KadeNode():
    '''
    Kademlia 最基礎結構，每個KadeNode代表一個peer，
       作為網路通信的一員
    
    Attributes:
        RSA: a RSA class use for rsa method
        web: a connect class content server and client socket for connect
        address: a tuple of (IPAddress, port) of server socket bind
        ID: the only ID of this node in the network
        NodeData: a NodeData class present this node, conntent RSA publicKey, address and ID
        table: a dict with key i: subtree split of the network and value:the bucket class of NodeData containt
             the route table of this node
        Savepath: path for the file save
    '''
    def __init__(self, **kwargs):
        self.RSA = RSA()
        self.web = Connect()
        self.address = self.web.GetServeAddress()
        self.ID = kwargs.get('ID', GetHash(self.address[0] + str(self.address[1])))#random ID here
        self.NodeData = NodeData(self.address, self.RSA.GetPublicKey(), self.ID)
        # routing table content all Kbucket, initial create empty table, key = distance, value = bucket
        #self.table = {i : KBucket(self.NodeData) for i in range(1, 128)}
        self.table = RouteTable(self.NodeData)
        self.SavePath = 'Save'
        # start for connect
        self.run()
        # create bucketj
        if kwargs.get('node', None) != None:
            self.update(kwargs['node'], getbucket = True)
        logger.info(f'node {self.ID} 上線了!!!')
        
        
    def update(self, node, getbucket = False):
        '''add new node to bucket in the table'''
        if node['ID'] == self.ID:
            return
        logger.debug(f'node {self.ID} 開始將 node {node["ID"]} 資料跟新於本地bucket中')
        #distance = CountDistance(self.ID, node['ID'])
        #self.table[distance].AddNode(node)
        self.table.AddNode(node)
        # get bucket of the node
        if getbucket:
            self.GetBucket(node['ID'])
        
    
    # request to other node
    # blocking
    def request(self, ID, *instruct, node = None):
        if node == None:
            node = self.GetNode(ID, closest = False)
        return Ask(self.NodeData.GetData(), 'request', *instruct,  address = node['address']) if node != None else None
          
          
    # send to other node
    # no blocking
    def send(self, ID, *instruct, node = None, content = ''):
        if node == None:
            node = self.GetNode(ID, closest = False)
        Ask(self.NodeData.GetData(), 'send', *instruct, address = node['address'], content = content)
        
    
    # get a node in the distance bucket, 
    # if ID is not none will count distance with ID and self ID and return the same distance node
    # return ( nodedata, socket )
    def GetDistanceNode(self, distance, ID = None, *, recursive = True, ExceptList = []):
        return (self.table[distance].GetNode(recursive = recursive, ExceptList = ExceptList) if ID == None
                    else self.table[CountDistance(self.ID, ID)].GetNode(ID, recursive = recursive, ExceptList = ExceptList))
        
    
    # if no argument is given, search for a exist node
    # get a node data, if the node not found, will return a same distance node if recurive is True
    # return ( nodedata, socket )
    def GetNode(self, ID, *, closest = True, ping = True, recursive = True, data = {}, ExceptList = []):
        '''
        get a node data, if the node not found, will return a same distance node if recurive is True
        '''
        return self.table.GetNode(ID, closest = closest, ping = ping, data = data, ExceptList = ExceptList)
        '''
        logger.debug(f'data["fail"] = {data.get("fail", None)}')
        ExceptList = data.get('fail', [])
        logger.debug(f'In GetNode ... ExceptList = {ExceptList}')
        if ID != None:
            distance = CountDistance(self.ID, ID)
            result = self.table[distance].GetNode(ID, recursive = recursive, ExceptList = ExceptList)
            if result == None and recursive:
                return self.GetDistanceNode(distance, ExceptList = ExceptList)
        else:
            for distance, bucket in self.table.items():
                if self.table[distance].length() != 0:
                    result = self.table[distance].GetNode(ExceptList = ExceptList)
                    if result != None:
                        break            
        return result
        '''
        
            
    def LookUp(self, ID, data = {}):
        '''
        find a node from network
        
        Args:
            ID: the node ID to find
            data: the request data from other node, default = {}
        '''
        logger.debug(f" in lookup data is {data}")
        logger.info(f'node {self.ID} 開始查找 node {ID} ， 雙方距離差距為 {int(CountDistance(self.ID, ID), 2)}')
        
        result = self.GetNode(ID, data = data)
        logger.info(f' LookUp result is {result}')
        
        if len(result) == 0:
            logger.info(f'no node has find...')
            # no node has find
            return ''
        
        elif result[0]['ID'] != ID or data.get('destination', {}).get('address', False):
            # the node not in bucket, start to search
            logger.info(f'node {self.ID} 準備向  result 中的 node 發出查找 node {ID} 的請求')
            for r in result:
                Ask(self.NodeData.GetData(), 'send', 'GET', 'node', ID, data = data, address = r['address'],
                    destination = data.get('destination', {'ID' : ID}))       
             
        elif data == {}:
            # return the correct node
            logger.info(f'node {ID} 存於本地， 回傳{result[0]}')
            return result[0]
        
        else:
            logger.info(f'node {ID} 存於本地， 向 node {result[0]["ID"]} 發出請求')
            Ask(self.NodeData.GetData(), 'send', 'GET', 'node', ID, data = data, address = result[0]['address'])
        
        return result

            
        '''
        if result == None:
            logger.info(f'查找結果： node {ID} 並不在 node {self.ID} 的 bucket中，開始向同距離的其他node查找')
            # if node not in table, ask other node in same distance to find the target node
            # SearchNode = [node, socket] or None
            SearchNode = self.GetDistanceNode(0, ID, ExceptList = data.get('fail', []))  
            if SearchNode != None:
                logger.info(f'node {self.ID} 準備向  node {SearchNode[0]["ID"]} 發出查找 node {ID} 的請求')
                Ask(self.NodeData.GetData(), 'send', 'GET', 'node', ID, data = data, connect = SearchNode, destination = {'ID' : ID})
            else:
                logger.info(f'同距離節點不存在或無法回應，請求拒絕，即將回退資料')
                Reject(self.NodeData.GetData(), data)
        elif data != {}:
            logger.info(f'查找結果： node {ID} 存在於 node {self.ID} 的 bucket中，開始請求node {ID} 聯繫 node {data["origin"]["ID"]}')
            Ask(self.NodeData.GetData(), 'send', 'GET', 'node', ID, data = data, connect = result)
        else:
            logger.info(f'node {ID} 存於本地，無需向網路查找')
        return result
        '''
       
    
    def GetBucket(self, ID = None):
        '''    
        initial to fullfill self bucket by ask other node to find self
        '''
        nodes = self.GetNode(ID)     
        # get a node, start to ask for bucket
        for node in nodes:
            logger.info(f'node {self.ID} 開始向 node {node["ID"]}， 請求find self')
            Ask(self.NodeData.GetData(), 'send', 'GET', 'node', self.ID, address = node['address'], destination = self.NodeData.GetData())       
        '''
            result = Ask(self.NodeData.GetData(), 'request', 'GET', 'bucket', address = connect)
            logger.debug(f'nodes = {result}')
            # get a dict of other table
            if result != None:
                logger.info(f'node {self.ID} 成功取得bucket，開始跟新到己方bucket')
                nodes = json.loads(result[0])
                for node in nodes:
                    self.update(node)
                logger.info(f'node {self.ID} 跟新bucket成功')
                return connect[0]['ID']
        return None
        '''
    
    # save node data
    def save(self, name = '', json = False):
        '''save self NodeData to a file'''
        name = (self.ID if name == '' else name) + '.txt'
        Path(self.SavePath).mkdir(parents=True, exist_ok=True) 
        folder = Path(self.SavePath)
        file = folder / name
        with file.open('wb') as f:
            pickle.dump(self.NodeData.GetData(), f)
        logger.debug(file.resolve())
            
        
    def UpLoadFile(self, file, data = {}, *, FilePath = ''):
        '''
        upload a file to network
        
        Args:
            file: file to upload, nust be a hashable value
            data: the request data from other node, default = {}
        '''
        
        # initial for kwargs
        kwargs = {}
        if data != {}:
            ExceptList = [saver[0]['ID'] for saver in data['content']['saver'] if (time.time() - saver[1]) < 86400]
            HashCode = data['instruct'][2]
            logger.debug(f"ExceptList = {ExceptList}, data['content']['saver'] = {data['content']['saver']}")    
        else:
            ExceptList = []
            HashCode = GetHashFile(Path(FilePath)) if FilePath != '' else GetHash(file)
            kwargs['content'] = {'FileID' : HashCode, 'saver' : [[self.NodeData.GetData(), time.time()]], 'file' : file}
            kwargs['destination'] = {'ID' : HashCode}
            
        logger.debug(f'HashCode = {HashCode}')    
        nodes = self.GetNode(HashCode, data = data, ExceptList = ExceptList)
        for node in nodes:
            logger.info(f'node {self.ID} 開始上傳檔案到網路，將資料傳給node {node["ID"]}')            
            Ask(self.NodeData.GetData(), 'send', 'POST', 'file', HashCode, address = node['address'],
                data = data, **kwargs)
        
        return nodes
        
             
    def GetFile(self, HashCode, data = {}):
        '''
        Get a file from network
        
        Args:
            HashCode: the Hashcode of file content
            data: the request data from other node, default = {}
        '''
        logger.info(f'node {self.ID} 收到GET file請求，開始查找本地有無該檔案')
        path = Path(self.SavePath, 'file', HashCode + '.txt')
        logger.debug(f'search: {path}')
        # strat to search file from web
        if not path.exists():
            logger.info(f'本地查無該檔案，向其他節點查找')
            # send to other node to search
            nodes = self.GetNode(HashCode, data = data)
            for node in nodes:
                logger.info(f'向node {node["ID"]} 發出GET file 請求')
                Ask(self.NodeData.GetData(), 'send', 'GET', 'file', HashCode, address = node['address'], data = data, content = {'FileID' : HashCode})
            return None
        
        else:
            logger.info(f'node {self.ID} 本地擁有該檔案，回傳該檔')
            file = json.loads(path.read_text())
            logger.debug(f'In GetFile, file is {file}')
            return file
    
    
    def GetAllNode(self):
        '''
        get all NodeData in table, return list of node
        
        Returns:
            list with all node in this
        '''
        result = {}
        for i in range(128):
            if self.table.amount[i] > 0:
                for k in self.table.table[i].bucket.keys():
                    result.update({i : self.table.table[i].bucket[k]})
        return result
            
    
    def run(self):
        # giveout self instance to server which will call handler to handle
        self.web.server.KadeNode = self
        self.web.run()
        
    
    def closs(self):
        pass