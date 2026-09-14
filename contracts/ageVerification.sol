// SPDX-License-Identifier: GPL-3.0

pragma solidity ^0.8.0;

contract AgeVerification {
    address public owner;

    modifier ownerOnly {
        require(msg.sender == owner, "Only the owner can use this function");
        _;
    }

    modifier issuerOnly {
        require(isIssuer[msg.sender], "Only an issuer can use this function");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function transferOwnership(address newOwner) public ownerOnly {
        require(newOwner != address(0), "Invalid address");
        owner = newOwner;
    }

    // Registry functions
    mapping(address => bool) public isIssuer;

    event IssuerAdded(address indexed issuer);
    event IssuerRevoked(address indexed issuer);

    // allows an issuer to revoke any attestations they made for a given address
    // issuers cannot revoke addresses that other issuers made, only ones they themselves issued
    // issuers also cannot revoke one attestation. revocations are for addresses only
    // thus any attestation made by a specific issuer for a specific address would be rendered invalid

    mapping(address => mapping(address => bool)) public revokedPairs;

    event AttestationRevoked(address indexed issuer, address indexed user);

    // this allows issuers to revoke attestations that they made directly
    // it is meant as a last resort option as it can be expensive and could struggle with scaling 
    // if issuers want to mass revoke attestations it would be easier to just generate a new Ethereum address and revoke the old one
    // this would make all attestations made with that address invalid, so some valid users could have their attestations invalidated
    function revokeAttestation(address _user) public issuerOnly {
        require(!revokedPairs[msg.sender][_user], "Already revoked");
        revokedPairs[msg.sender][_user] = true;
        emit AttestationRevoked(msg.sender, _user);
    }

    // checks if an issuer is trusted, can also be done via the public registry of keys
    function isTrusted(address _address) public view returns (bool) {
        return isIssuer[_address];
    }

    // allows contract owner to add an address to the registry
    // should be done if/when an issuer verifiably meets some standard (i.e. KYC)
    function addAddress(address _address) public ownerOnly {
        require(!isIssuer[_address], "Already added");
        isIssuer[_address] = true;
        emit IssuerAdded(_address);
    }

    // allows contract owner to remove an address from the registry
    // should be done if/when an issuer fails to uphold the standard (i.e. loses certification)
    function revokeAddress(address _address) public ownerOnly {
        require(isIssuer[_address], "Not in registry");
        isIssuer[_address] = false;
        emit IssuerRevoked(_address);
    }

    // recovers the signer address from a hash and signature
    function recoverSigner(bytes32 hash, bytes memory sig) internal pure returns (address) {
        bytes32 ethHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", hash));
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := mload(add(sig, 32))
            s := mload(add(sig, 64))
            v := byte(0, mload(add(sig, 96)))
        }
        return ecrecover(ethHash, v, r, s);
    }

    // verification functions
    event IssuerVerified (address indexed issuer, bool isVerified);

    function issuerVerify(address issuer, uint256 nonce, bytes memory verify_signature) public returns (bool) {
        // Check issuer is in the trusted registry
        require(isIssuer[issuer], "Issuer is not trusted");

        // Hash the issuer's address and nonce — this is what the issuer signed off-chain
        bytes32 issuerHash = keccak256(abi.encodePacked(issuer, nonce));
        address recoveredIssuer = recoverSigner(issuerHash, verify_signature);

        require(recoveredIssuer == issuer, "Invalid issuer signature");

        emit IssuerVerified(issuer, true);
        return true;
    }

    event AgeVerified(address indexed user, address indexed issuer, bool is18plus);

    function verifyAge(
        address issuer,
        address user,
        bool is18plus,
        uint256 nonce,
        uint256 attestation_expiration,
        bytes memory issuer_signature,
        bytes memory user_signature
    ) public returns (bool) {

        // issuer must be in registry
        require(isIssuer[issuer], "Issuer is untrusted");

        // the issuer-user pair must not be revoked
        require(!revokedPairs[issuer][user], "Attestation revoked for this issuer");

        // signature must not be expired
        require(block.timestamp <= attestation_expiration, "Signature expired");

        // Hash the attestation data for the issuer's signature
        bytes32 attestation = keccak256(abi.encodePacked(user, is18plus, attestation_expiration));
        address recoveredIssuer = recoverSigner(attestation, issuer_signature);
        require(recoveredIssuer == issuer, "Invalid issuer signature");

        // Hash the user's agreement
        bytes32 userAgreement = keccak256(abi.encodePacked(nonce));
        address recoveredUser = recoverSigner(userAgreement, user_signature);
        require(recoveredUser == user, "Invalid user signature");

        emit AgeVerified(user, issuer, is18plus);
        return is18plus;
    }
}

