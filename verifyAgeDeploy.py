from solcx import compile_standard
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
import json, sys
from solcx import compile_standard, install_solc

# This file allows the contract to be compiled and deployed on a local blockchain network
# It also includes some sample interactions used for testing the contract

def compile_contract():
    install_solc('0.8.0')
    with open("ageVerification.sol", "r") as file:
        content = file.read()

    compiled_sol = compile_standard({
        "language": "Solidity",
        "sources": {"ageVerification.sol": {"content": content}},
        "settings": {"outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}}},
    }, solc_version="0.8.0")

    abi = compiled_sol["contracts"]["ageVerification.sol"]["AgeVerification"]["abi"]
    bytecode = compiled_sol["contracts"]["ageVerification.sol"]["AgeVerification"]["evm"]["bytecode"]["object"]
    return abi, bytecode


def send_tx(web3, contract_fn, private_key, public_key):
    tx = contract_fn.build_transaction({
        'from': public_key,
        'nonce': web3.eth.get_transaction_count(public_key),
        'gasPrice': "0x0"
    })
    signed = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    return web3.eth.wait_for_transaction_receipt(tx_hash)


if __name__ == "__main__":
    do_deploy = int(sys.argv[1])
    node_port = sys.argv[2]

    web3 = Web3(Web3.HTTPProvider(f"http://localhost:{node_port}"))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    # Besu network owner account
    private_key = "0x74d507033d2c0f22b34c42ea1bf2d4f86c7f2061e19984a824d95603641a2907"
    public_key = Web3.to_checksum_address("0x94b7c73603c2468e23fc83f9d9aa25981ae4e193")

    abi, bytecode = compile_contract()

    if do_deploy == 1:
        AgeVerificationContract = web3.eth.contract(abi=abi, bytecode=bytecode)

        construct_tx = AgeVerificationContract.constructor().build_transaction({
            'from': public_key,
            'nonce': web3.eth.get_transaction_count(public_key),
            'gasPrice': "0x0"
        })
        signed_tx = web3.eth.account.sign_transaction(construct_tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        print(f"Deploying... Hash: {tx_hash.hex()}")
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        address = receipt.contractAddress

        with open("contract_address.json", "w") as f:
            json.dump({"contract_address": address}, f)
        print(f"Deployed to: {address}")
    else:
        with open("contract_address.json", "r") as f:
            address = json.load(f)["contract_address"]

    contract = web3.eth.contract(address=address, abi=abi)

    # Load verification data produced by ageVerify.py
    with open("verification_data.json", "r") as f:
        data = json.load(f)

    # Register the issuer as trusted in the contract registry
    issuer_address = Web3.to_checksum_address(data["issuer_address"])
    print(f"\nRegistering issuer: {issuer_address}")
    receipt = send_tx(web3, contract.functions.addAddress(issuer_address), private_key, public_key)
    print(f"Issuer registered. Tx: {receipt.transactionHash.hex()}")

    # Call verifyAge with all data from verification_data.json
    print("\nCalling verifyAge...")
    receipt = send_tx(web3, contract.functions.verifyAge(
        issuer_address,
        Web3.to_checksum_address(data["user_address"]),
        data["is18plus"],
        data["nonce"],
        data["attestation_expiration"],
        bytes.fromhex(data["issuer_signature"].removeprefix("0x")),
        bytes.fromhex(data["user_challenge_signature"].removeprefix("0x"))
    ), private_key, public_key)

    print(f"verifyAge tx: {receipt.transactionHash.hex()}")
    print(f"Status: {'SUCCESS' if receipt.status == 1 else 'FAILED'}")


    logs = contract.events.AgeVerified().process_receipt(receipt)
    is18plus = logs[0]['args']['is18plus']
    print(f"verifyAge tx: {receipt.transactionHash.hex()}")
    print(f"Is 18+: {is18plus}")
    print(f"Access granted: {is18plus}")