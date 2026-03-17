<?xml version="1.0" encoding="UTF-8"?>
<schema xmlns="http://purl.oclc.org/dsdl/schematron">
    <title>GİB UBL-TR 1.2.1 Temel Fatura Kontrolleri (Demo)</title>
    <ns prefix="cac" uri="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"/>
    <ns prefix="cbc" uri="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"/>
    <ns prefix="ext" uri="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"/>
    <ns prefix="ubltr" uri="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"/>

    <pattern id="Fatura_Temel_Kurallar">
        <rule context="/">
            <assert test="ubltr:Invoice" flag="fatal">Kök eleman 'Invoice' (Fatura) olmalıdır. Bu bir UBL-TR Faturası değildir.</assert>
        </rule>
        
        <rule context="//ubltr:Invoice">
            <assert test="cbc:UBLVersionID" flag="warning">UBLVersionID elemanı bulunamadı. GİB standartlarında '2.1' olması beklenir.</assert>
            <assert test="cbc:CustomizationID" flag="fatal">CustomizationID elemanı zorunludur. (Örn: TR1.2)</assert>
            <assert test="cbc:ProfileID" flag="fatal">ProfileID (Senaryo) elemanı zorunludur. (Örn: TICARIFATURA, TEMELFATURA)</assert>
            <assert test="cbc:ID" flag="fatal">Fatura numarası (ID) zorunludur ve 16 haneli olmalıdır.</assert>
            
            <assert test="cac:AccountingSupplierParty" flag="fatal">AccountingSupplierParty (Satıcı Bilgileri) zorunludur.</assert>
            <assert test="cac:AccountingCustomerParty" flag="fatal">AccountingCustomerParty (Alıcı Bilgileri) zorunludur.</assert>
            <assert test="cac:InvoiceLine" flag="fatal">Faturada en az bir adet InvoiceLine (Fatura Satırı) bulunmalıdır.</assert>
        </rule>
        
        <rule context="//cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme">
            <assert test="cbc:CompanyID" flag="fatal">Satıcının Vergi Kimlik Numarası veya TC Kimlik Numarası (CompanyID) zorunludur.</assert>
        </rule>
        
        <rule context="//cac:AccountingCustomerParty/cac:Party/cac:PartyTaxScheme">
            <assert test="cbc:CompanyID" flag="fatal">Alıcının Vergi Kimlik Numarası veya TC Kimlik Numarası (CompanyID) zorunludur.</assert>
        </rule>
    </pattern>
</schema>
