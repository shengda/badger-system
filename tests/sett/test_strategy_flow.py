from helpers.time_utils import days
import brownie
import pytest
from brownie import *
from helpers.constants import *
from helpers.sett.SnapshotManager import SnapshotManager
from tests.conftest import badger_single_sett
from tests.helpers import getTokenMetadata
from tests.test_recorder import EventRecord, TestRecorder


# @pytest.mark.skip()
@pytest.mark.parametrize(
    "settId",
    [
        "native.badger",
        "native.renCrv",
        "native.sbtcCrv",
        "native.tbtcCrv",
        # "pickle.renCrv",
        "harvest.renCrv",
        "native.uniBadgerWbtc",
    ],
)
def test_deposit_withdraw_single_user_flow(settId):
    badger = badger_single_sett(settId)
    controller = badger.getController(settId)
    sett = badger.getSett(settId)
    strategy = badger.getStrategy(settId)
    want = badger.getStrategyWant(settId)

    snap = SnapshotManager(badger, settId)

    deployer = badger.deployer
    randomUser = accounts[6]

    print(want, want.address, want.totalSupply(), deployer)

    # Deposit
    depositAmount = int(want.balanceOf(deployer) * 0.8)

    want.approve(sett, MaxUint256, {"from": deployer})
    snap.settDeposit(depositAmount, {"from": deployer})

    # Earn
    with brownie.reverts("onlyAuthorizedActors"):
        sett.earn({"from": randomUser})

    min = sett.min()
    max = sett.max()
    remain = max - min

    assert sett.keeper() == deployer

    snap.settEarn({"from": deployer})

    chain.sleep(15)
    chain.mine(1)

    snap.settWithdraw(depositAmount // 2, {"from": deployer})

    chain.sleep(10000)
    chain.mine(1)

    snap.settWithdrawAll({"from": deployer})


@pytest.mark.skip()
@pytest.mark.parametrize(
    "settId",
    [
        "native.renCrv",
        "native.badger",
        "native.sbtcCrv",
        "native.tbtcCrv",
        # "pickle.renCrv",
        "harvest.renCrv",
        "native.uniBadgerWbtc",
    ],
)
def test_single_user_harvest_flow(settId):
    suiteName = "test_single_user_harvest_flow" + ": " + settId
    testRecorder = TestRecorder(suiteName)

    badger = badger_single_sett(settId)
    controller = badger.getController(settId)
    sett = badger.getSett(settId)
    strategy = badger.getStrategy(settId)
    want = badger.getStrategyWant(settId)

    snap = SnapshotManager(badger, settId)

    deployer = badger.deployer
    randomUser = accounts[6]

    tendable = strategy.isTendable()

    startingBalance = want.balanceOf(deployer)

    depositAmount = Wei("1 ether")
    assert startingBalance >= depositAmount

    # Deposit
    want.approve(sett, MaxUint256, {"from": deployer})
    snap.settDeposit(depositAmount, {"from": deployer})

    # Earn
    snap.settEarn(depositAmount, {"from": deployer})

    if tendable:
        with brownie.reverts("onlyAuthorizedActors"):
            strategy.tend({"from": randomUser})

        snap.settTend({"from": deployer})

    chain.sleep(days(0.5))
    chain.mine()

    if tendable:
        snap.settTend({"from": deployer})

    chain.sleep(days(1))
    chain.mine()

    with brownie.reverts("onlyAuthorizedActors"):
        strategy.harvest({"from": randomUser})

    snap.settHarvest({"from": deployer})

    chain.sleep(days(1))
    chain.mine()

    if tendable:
        snap.settTend({"from": deployer})

    chain.sleep(days(3))
    chain.mine()

    snap.settHarvest({"from": deployer})

    snap.settWithdrawAll({"from": deployer})

    endingBalance = want.balanceOf(deployer)
    assert endingBalance > startingBalance


@pytest.mark.skip()
@pytest.mark.parametrize(
    "settId",
    [
        "native.renCrv",
        "native.badger",
        "native.sbtcCrv",
        "native.tbtcCrv",
        # "pickle.renCrv",
        "harvest.renCrv",
        "native.uniBadgerWbtc",
    ],
)
def test_migrate_single_user(settId):
    badger = badger_single_sett(settId)
    controller = badger.getController(settId)
    sett = badger.getSett(settId)
    strategy = badger.getStrategy(settId)
    want = badger.getStrategyWant(settId)

    deployer = badger.deployer
    randomUser = accounts[6]

    startingBalance = want.balanceOf(deployer)

    depositAmount = Wei("1 ether")
    assert startingBalance >= depositAmount

    # Deposit
    want.approve(sett, MaxUint256, {"from": deployer})
    sett.deposit(depositAmount, {"from": deployer})
    after = sett_snapshot(sett, strategy, deployer)

    chain.sleep(15)
    chain.mine()

    sett.earn({"from": deployer})

    chain.snapshot()

    # Test no harvests
    chain.sleep(days(2))
    chain.mine()

    before = {"settWant": want.balanceOf(sett), "stratWant": strategy.balanceOf()}

    with brownie.reverts():
        controller.withdrawAll(strategy.want(), {"from": randomUser})

    controller.withdrawAll(strategy.want(), {"from": deployer})

    after = {"settWant": want.balanceOf(sett), "stratWant": strategy.balanceOf()}

    assert after["settWant"] > before["settWant"]
    assert after["stratWant"] < before["stratWant"]
    assert after["stratWant"] == 0

    # Test tend only
    if strategy.isTendable():
        chain.revert()

        chain.sleep(days(2))
        chain.mine()

        strategy.tend({"from": deployer})

        before = {"settWant": want.balanceOf(sett), "stratWant": strategy.balanceOf()}

        with brownie.reverts():
            controller.withdrawAll(strategy.want(), {"from": randomUser})

        controller.withdrawAll(strategy.want(), {"from": deployer})

        after = {"settWant": want.balanceOf(sett), "stratWant": strategy.balanceOf()}

        assert after["settWant"] > before["settWant"]
        assert after["stratWant"] < before["stratWant"]
        assert after["stratWant"] == 0

    # Test harvest, with tend if tendable
    chain.revert()

    chain.sleep(days(1))
    chain.mine()

    if strategy.isTendable():
        strategy.tend({"from": deployer})

    chain.sleep(days(1))
    chain.mine()

    before = {
        "settWant": want.balanceOf(sett),
        "stratWant": strategy.balanceOf(),
        "rewardsWant": want.balanceOf(controller.rewards()),
    }

    with brownie.reverts():
        controller.withdrawAll(strategy.want(), {"from": randomUser})

    controller.withdrawAll(strategy.want(), {"from": deployer})

    after = {"settWant": want.balanceOf(sett), "stratWant": strategy.balanceOf()}

    assert after["settWant"] > before["settWant"]
    assert after["stratWant"] < before["stratWant"]
    assert after["stratWant"] == 0


@pytest.mark.skip()
@pytest.mark.parametrize(
    "settId",
    [
        "native.renCrv",
        "native.badger",
        "native.sbtcCrv",
        "native.tbtcCrv",
        # "pickle.renCrv",
        "harvest.renCrv",
        "native.uniBadgerWbtc",
    ],
)
def test_withdraw_other(settId):
    """
    - Controller should be able to withdraw other tokens
    - Controller should not be able to withdraw core tokens
    - Non-controller shouldn't be able to do either
    """
    badger = badger_single_sett(settId)
    controller = badger.getController(settId)
    sett = badger.getSett(settId)
    strategy = badger.getStrategy(settId)
    want = badger.getStrategyWant(settId)

    deployer = badger.deployer
    randomUser = accounts[6]

    startingBalance = want.balanceOf(deployer)

    depositAmount = Wei("1 ether")
    print(getTokenMetadata(want.address), startingBalance)
    assert startingBalance >= depositAmount

    # Deposit
    want.approve(sett, MaxUint256, {"from": deployer})
    sett.deposit(depositAmount, {"from": deployer})
    after = sett_snapshot(sett, strategy, deployer)

    chain.sleep(15)
    chain.mine()

    sett.earn({"from": deployer})

    chain.sleep(days(0.5))
    chain.mine()

    if strategy.isTendable():
        strategy.tend({"from": deployer})

    strategy.harvest({"from": deployer})

    chain.sleep(days(0.5))
    chain.mine()

    mockAmount = Wei("1000 ether")
    mockToken = MockToken.deploy({"from": deployer})
    mockToken.initialize([strategy], [mockAmount], {"from": deployer})

    assert mockToken.balanceOf(strategy) == mockAmount

    # Should not be able to withdraw protected tokens
    protectedTokens = strategy.getProtectedTokens()
    print(protectedTokens)
    for token in protectedTokens:
        with brownie.reverts():
            controller.inCaseStrategyTokenGetStuck(strategy, token, {"from": deployer})

    # Should send balance of non-protected token to sender
    controller.inCaseStrategyTokenGetStuck(strategy, mockToken, {"from": deployer})

    with brownie.reverts():
        controller.inCaseStrategyTokenGetStuck(
            strategy, mockToken, {"from": randomUser}
        )

    assert mockToken.balanceOf(controller) == mockAmount


@pytest.mark.skip()
@pytest.mark.parametrize(
    "settId",
    [
        "native.renCrv",
        "native.badger",
        "native.sbtcCrv",
        "native.tbtcCrv",
        # "pickle.renCrv",
        "harvest.renCrv",
        "native.uniBadgerWbtc",
    ],
)
def test_single_user_harvest_flow_remove_fees(settId):
    suiteName = "test_single_user_harvest_flow_remove_fees" + ": " + settId
    testRecorder = TestRecorder(suiteName)

    badger = badger_single_sett(settId)
    controller = badger.getController(settId)
    sett = badger.getSett(settId)
    strategy = badger.getStrategy(settId)
    want = badger.getStrategyWant(settId)

    deployer = badger.deployer
    randomUser = accounts[6]

    tendable = strategy.isTendable()

    startingBalance = want.balanceOf(deployer)

    depositAmount = Wei("1 ether")
    assert startingBalance >= depositAmount

    # Deposit
    before = sett_snapshot(sett, strategy, deployer)
    want.approve(sett, MaxUint256, {"from": deployer})
    sett.deposit(depositAmount, {"from": deployer})
    after = sett_snapshot(sett, strategy, deployer)

    confirm_deposit(before, after, deployer, depositAmount)

    # Earn
    before = sett_snapshot(sett, strategy, deployer)
    sett.earn({"from": deployer})
    after = sett_snapshot(sett, strategy, deployer)

    confirm_earn(before, after)

    chain.sleep(days(0.5))
    chain.mine()

    if tendable:
        before = sett_snapshot(sett, strategy, deployer)
        tx = strategy.tend({"from": deployer})
        after = sett_snapshot(sett, strategy, deployer)
        testRecorder.add_record(EventRecord("Tend", tx.events, tx.timestamp))

        confirm_tend(before, after, deployer)

    chain.sleep(days(1))
    chain.mine()

    with brownie.reverts("onlyAuthorizedActors"):
        strategy.harvest({"from": randomUser})

    before = sett_snapshot(sett, strategy, deployer)
    tx = strategy.harvest({"from": deployer})
    after = sett_snapshot(sett, strategy, deployer)
    testRecorder.add_record(EventRecord("Harvest", tx.events, tx.timestamp))
    testRecorder.print_to_file(suiteName + ".json")

    confirm_harvest(before, after, deployer)

    after_harvest = sett_snapshot(sett, strategy, deployer)

    print("tx.events", tx.events)

    # Harvesting on the HarvestMetaFarm does not increase the underlying position, it sends rewards to the rewardsTree
    # For HarvestMetaFarm, we expect FARM rewards to be distributed to rewardsTree
    if settId == "harvest.renCrv":
        assert want.balanceOf(controller.rewards() > 0)

    # For most Setts, harvesting should increase the underlying position
    else:
        assert want.balanceOf(controller.rewards() > 0)

    chain.sleep(days(1))
    chain.mine()

    if tendable:
        tx = strategy.tend({"from": deployer})
        testRecorder.add_record(EventRecord("Tend", tx.events, tx.timestamp))

    chain.sleep(days(3))
    chain.mine()

    before_harvest = sett_snapshot(sett, strategy, deployer)
    tx = strategy.harvest({"from": deployer})
    after_harvest = sett_snapshot(sett, strategy, deployer)
    testRecorder.add_record(EventRecord("Harvest", tx.events, tx.timestamp))

    harvested = tx.events["Harvest"][0]["harvested"]
    if settId != "harvest.renCrv":
        assert harvested > 0
        assert (
            after_harvest.sett.pricePerFullShare > before_harvest.sett.pricePerFullShare
        )
        assert after_harvest.strategy.balanceOf > before_harvest.strategy.balanceOf

    sett.withdrawAll({"from": deployer})

    endingBalance = want.balanceOf(deployer)

    report = {
        "time": "4 days",
        "gains": endingBalance - startingBalance,
        "gainsPercentage": (endingBalance - startingBalance) / startingBalance,
    }

    # testRecorder.add_record(EventRecord("Final Report", report, 0))
    testRecorder.print_to_file(suiteName + ".json")
