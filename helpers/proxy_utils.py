from brownie import *

from helpers.registry import registry


def deploy_proxy_admin(deployer):
    abi = registry.open_zeppelin.artifacts["ProxyAdmin"]["abi"]
    bytecode = registry.open_zeppelin.artifacts["ProxyAdmin"]["bytecode"]

    ProxyAdmin = web3.eth.contract(abi=abi, bytecode=bytecode)

    deploy_txn = ProxyAdmin.constructor().buildTransaction()
    tx = deployer.transfer(data=deploy_txn["data"])

    return Contract.from_abi(
        "ProxyAdmin", web3.toChecksumAddress(tx.contract_address), abi,
    )


def deploy_proxy(contractName, logicAbi, logic, proxyAdmin, initializer, deployer):
    abi = registry.open_zeppelin.artifacts["AdminUpgradeabilityProxy"]["abi"]
    bytecode = registry.open_zeppelin.artifacts["AdminUpgradeabilityProxy"]["bytecode"]

    AdminUpgradeabilityProxy = web3.eth.contract(abi=abi, bytecode=bytecode)

    deploy_txn = AdminUpgradeabilityProxy.constructor(
        logic, proxyAdmin, web3.toBytes(hexstr=initializer)
    ).buildTransaction()

    tx = deployer.transfer(data=deploy_txn["data"])

    print("Deployed Proxy: ", tx.contract_address)
    return Contract.from_abi(contractName, tx.contract_address, logicAbi)

