// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TransactionAuditor
 * @dev Smart contract for maintaining tamper-evident audit hashes of financial transactions
 * evaluated by an AI fraud detection system.
 * 
 * Notice: This contract stores only cryptographic fingerprints (SHA-256 hashes) and metadata,
 * preserving confidentiality without storing sensitive transaction figures or PII on-chain.
 */
contract TransactionAuditor {
    struct AuditRecord {
        string transactionRef;      // Unique business reference (e.g. TXN-1001)
        string auditHash;           // SHA-256 hash of the canonical transaction audit packet
        uint256 timestamp;          // On-chain registration timestamp
        address recordedBy;         // Address of the auditor/system that logged this record
        bool exists;                // Existence guard
    }

    // Mapping from transaction reference to its immutable audit record
    mapping(string => AuditRecord) private records;

    // Track list of all transaction references
    string[] private transactionRefs;

    // Contract administrator / deployer
    address public owner;

    // Events
    event AuditRecordLogged(
        string indexed transactionRef,
        string auditHash,
        uint256 timestamp,
        address indexed recordedBy
    );

    event AuditRecordQueried(
        string indexed transactionRef,
        bool verified,
        uint256 queriedAt
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Only contract owner can execute this action");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @dev Log a new audit hash for a transaction.
     * Reverts if the transaction reference has already been committed to guarantee immutability.
     */
    function logAuditRecord(string memory _transactionRef, string memory _auditHash) public {
        require(bytes(_transactionRef).length > 0, "Transaction reference cannot be empty");
        require(bytes(_auditHash).length > 0, "Audit hash cannot be empty");
        require(!records[_transactionRef].exists, "Audit record already exists and is immutable");

        records[_transactionRef] = AuditRecord({
            transactionRef: _transactionRef,
            auditHash: _auditHash,
            timestamp: block.timestamp,
            recordedBy: msg.sender,
            exists: true
        });

        transactionRefs.push(_transactionRef);

        emit AuditRecordLogged(_transactionRef, _auditHash, block.timestamp, msg.sender);
    }

    /**
     * @dev Retrieve the audit record for a given transaction reference.
     */
    function getAuditRecord(string memory _transactionRef) 
        external 
        view 
        returns (
            string memory transactionRef,
            string memory auditHash,
            uint256 timestamp,
            address recordedBy,
            bool exists
        ) 
    {
        AuditRecord memory record = records[_transactionRef];
        return (
            record.transactionRef,
            record.auditHash,
            record.timestamp,
            record.recordedBy,
            record.exists
        );
    }

    /**
     * @dev Verify whether a calculated hash matches the on-chain stored hash.
     */
    function verifyRecordHash(string memory _transactionRef, string memory _calculatedHash) 
        external 
        view 
        returns (bool matches, string memory storedHash, uint256 timestamp) 
    {
        require(records[_transactionRef].exists, "Transaction reference not found on blockchain");
        AuditRecord memory record = records[_transactionRef];
        
        // Compare SHA-256 strings
        bool isMatching = keccak256(bytes(record.auditHash)) == keccak256(bytes(_calculatedHash));
        return (isMatching, record.auditHash, record.timestamp);
    }

    /**
     * @dev Get total count of logged records.
     */
    function getTotalRecordCount() external view returns (uint256) {
        return transactionRefs.length;
    }

    /**
     * @dev Get transaction reference by index.
     */
    function getTransactionRefByIndex(uint256 index) external view returns (string memory) {
        require(index < transactionRefs.length, "Index out of bounds");
        return transactionRefs[index];
    }
}
