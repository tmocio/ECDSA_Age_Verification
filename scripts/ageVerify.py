from eth_account import Account
from eth_account.messages import encode_defunct
import time 
from web3 import Web3
import os 
import json

# First we need keys for each party 
# In practice, the issuer would have their own key pair but we generate one here for demonstration.
# Age verification cannot be done fully decentralized. We need some trusted source that can attest to people's ages.
# In theory it could be a bank or government. But it can be anyone who achieves some set standard regarding data and honesty. 
# Through a practice similar to KYC.
# In this demonstration the 'trusted source' is known as the 'issuer'.

issuer = Account.create()
issuer_address = issuer.address
issuer_private_key = issuer.key

print("--- ISSUER KEY PAIR ---")
print(f"Address:     {issuer_address}")
print(f"Private Key: {issuer_private_key.hex()}")
print("\n")
# We also need keys for the individual. Hereby known as the 'user'.
# It is not required that the issuer makes the users keys, in theory anyone could make the keys as long as both the user and issuer use the correct ones. 
# In practice the user could make the keys, and give their address to the issuer when they want to verify.


user = Account.create()
user_address = user.address
user_private_key = user.key

print("--- USER KEY PAIR ---")
print(f"Address:     {user_address}")
print(f"Private Key: {user_private_key.hex()}")
print("\n")

# In the demonstration we will use only these keys, but this system is scalable across both users and issuers. 


# The user must first determine if the issuer they interact with is actually trusted. To do this, they issue a challenge.
# First, they generate a nonce
user_nonce = int.from_bytes(os.urandom(32), 'big')

# Then they send this nonce to the issuer and ask them to sign it using their private key
user_nonce_hash = Web3.solidity_keccak(['uint256'], [user_nonce])
issuer_sign = Account.sign_message(encode_defunct(user_nonce_hash), issuer_private_key)
issuer_challenge_signature = issuer_sign.signature

# The issuer will then send the signature back to the user, and the user can verify the signature 
# Recreate the same hash
user_nonce_hash = Web3.solidity_keccak(['uint256'], [user_nonce])
# Recover the signer
recovered_issuer_address = Account.recover_message(encode_defunct(user_nonce_hash), signature=issuer_challenge_signature)

# Check it matches
print("Does the signature address match the initial issuer:", recovered_issuer_address == issuer_address)
print('\n')
# The user can then check that this address exists in the smart contract 'trusted' registry.

# Now that we have the keys for each party, and we know the issuer is trusted, we can create the attestation.
# The user would either submit their identity information, or use the existing one on file held by the issuer.
# And the issuer would use them to create an attestation. This would act as a digital ID card holding the users information. 
# The system is designed in such a way that the attestation contains only the necessary information to verify age, and nothing else. 

# For demonstration, this is the users personal information 

user_info = {
    "name": "John Smith",
    "age": 18,
    "address": user_address,
}

# The issuer can then use this information to create an identifier based on their age
if user_info['age'] >= 18:
  is18plus = True
else:
  is18plus = False

print("--- USER AGE IDENTIFIER ---")
print("Is user 18+:", is18plus)


# Before we can create the attestation we need one more thing, an expiration date.
# This is arbitrary, just added to require users to resubmit their info periodically. 
# It also lessens the damage that fraudulent attestations can cause. 
# I added it to make attestations mirror real ID cards more closely. 

attestation_expiration = int(time.time()) + 31556926

# Now the attestation can be made 

attestation_hash = Web3.solidity_keccak(
    ['address', 'bool', 'uint256'],
    [user_address, is18plus, attestation_expiration]
)

issuer_signed = Account.sign_message(encode_defunct(attestation_hash), issuer_private_key)
issuer_signature = issuer_signed.signature

# The attestion is a hash of the users address, the boolean identifier, and the expiration.
# It is then signed by the issuer using their private key. 

print("\n--- ATTESTATION ---")
print(f"User Address:           {user_address}")
print(f"Is 18+:                 {is18plus}")
print(f"Expiration (unix):      {attestation_expiration}")
print(f"Issuer Signature:       {issuer_signature.hex()}")

# Now the issuer can send all of the data to the user and they can store it.
# How it is sent, and where it is stored still need to be worked out.


print("\n--- DATA SENT TO USER ---")
print(f"Issuer Address:         {issuer_address}")
print(f"User Address:           {user_address}")
print(f"Is 18+:                 {is18plus}")
print(f"Expiration (unix):      {attestation_expiration}")
print(f"Issuer Signature:       {issuer_signature.hex()}")

# Now the issuer is no longer needed. They do not need to store or record any of the information listed above. 
# The user can store that information on their device securely in some way. 

# Now let's say that the user wants to access a site or application (or anything) that requires age verification. 
# Hereby known as the verifier. 
# The user would first prompt the verifier, letting them know that they want to verify their age. 
# The site would first generate a nonce.

nonce = int.from_bytes(os.urandom(32), 'big')

# The user would then sign the nonce using their own private key. 

nonce_hash = Web3.solidity_keccak(['uint256'], [nonce])
user_signed = Account.sign_message(encode_defunct(nonce_hash), user_private_key)
user_challenge_signature = user_signed.signature
 
print("\n--- NONCE CHALLENGE ---")
print(f"Nonce:                  {nonce}")
print(f"User Challenge Signature:         {user_challenge_signature.hex()}")

# The reason I include the nonce, is because the verifier must ensure that the person trying to verify is the person that the attestation corresponds with 
# In other words, we want to check that the user possesses the private key that corresponds with the address in the attestation 
# Otherwise people could just share attestations and the address would be meaningless. 
# Obviously there is a flaw here, what if people share private keys. 
# I think its reasonable to assume that this wouldn't happen. 
# But we can alter the way that keys are given to the user and stored to try to make sharing private keys infeasible. 

# Now that the nonce has been signed, the user can send the entire data set. 

print("--- DATA SENT TO VERIFIER TO VERIFY ---")
print(f"User Address:                 {user_address}")
print(f"Issuer Address:               {issuer_address}")
print(f"Is 18+:                       {is18plus}")
print(f"Expiration (unix):            {attestation_expiration}")
print(f"Issuer Signature:             {issuer_signature.hex()}")
print(f"User Challenge Signature:     {user_challenge_signature.hex()}")


# Now that the verifier has that data they must first add the nonce they sent
# and then package the data
verification_data = {
    "issuer_address": issuer_address,
    "user_address": user_address,
    "is18plus": is18plus,
    "nonce": nonce,
    "attestation_expiration": attestation_expiration,
    "issuer_signature": issuer_signature,
    "user_challenge_signature": user_challenge_signature
}

# Now the verifier must interact with the blockchain
# They will call our smart contract (ageVerification.sol) 
# The function verifyAge takes all of the data listed above as arguments
# It verifies both the issuer_signature and the user_challenge_signature
# It also verifies the attestation_expiration against the current time
# Lastly, it checks that the issuer_address is contained within the isIssuer mapping
# This verifies that the issuer is considered trusted

# Once we know:
# The issuer is trusted
# The attestation was correctly signed by the issuer 
# The attestation is not expired
# The nonce was correctly signed
# The is18plus identifier is True

# We can allow access to the site/app. Any other result and they reject access.



# We can export the data as JSON 

with open("verification_data.json", "w") as f:
    json.dump({
        "issuer_address": issuer_address,
        "user_address": user_address,
        "is18plus": is18plus,
        "nonce": nonce,
        "attestation_expiration": attestation_expiration,
        "issuer_signature": issuer_signature.hex(),
        "user_challenge_signature": user_challenge_signature.hex()
    }, f, indent=2)

print("\nData written to verification_data.json")
