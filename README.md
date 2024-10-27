<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>

<h1>BackendPython - Bank Management System API</h1>

<p>A Django-based REST API for managing bank accounts, transactions, loans, and user authentication.</p>

<h2>Project Overview</h2>
<p>This API provides endpoints for users to create bank accounts, perform transactions, manage loans, and handle authentication. It includes operations such as deposits, withdrawals, transfers, and loan management with multi-currency support.</p>

<h2>Endpoints</h2>
<table>
    <thead>
        <tr>
            <th>Method</th>
            <th>Endpoint</th>
            <th>Description</th>
        </tr>
    </thead>
    <tbody>
        <tr><td>POST</td><td>/api/bankaccount/</td><td>Create a new bank account</td></tr>
        <tr><td>PATCH</td><td>/api/bankaccount/{id}/activate/</td><td>Activate a suspended bank account</td></tr>
        <tr><td>DELETE</td><td>/api/bankaccount/{id}/close/</td><td>Close a bank account</td></tr>
        <tr><td>PATCH</td><td>/api/bankaccount/{id}/suspend/</td><td>Suspend a bank account</td></tr>
        <tr><td>GET</td><td>/api/bankoperations/bankaccounts/balance/</td><td>Retrieve balance of a bank account</td></tr>
        <tr><td>POST</td><td>/api/bankoperations/bankaccounts/deposit/</td><td>Deposit funds to an account</td></tr>
        <tr><td>GET</td><td>/api/bankoperations/bankaccounts/transactions/</td><td>Retrieve account transactions</td></tr>
        <tr><td>POST</td><td>/api/bankoperations/bankaccounts/transfer/</td><td>Transfer funds between accounts</td></tr>
        <tr><td>POST</td><td>/api/bankoperations/bankaccounts/withdraw/</td><td>Withdraw funds from an account</td></tr>
        <tr><td>GET</td><td>/api/bankoperations/loans/customer-loans/</td><td>Retrieve customer loans</td></tr>
        <tr><td>POST</td><td>/api/bankoperations/loans/grant/</td><td>Grant a loan</td></tr>
        <tr><td>POST</td><td>/api/bankoperations/loans/repay/</td><td>Repay a loan</td></tr>
        <tr><td>GET</td><td>/api/schema/</td><td>API schema</td></tr>
        <tr><td>POST</td><td>/api/user/create/</td><td>Create a new user</td></tr>
        <tr><td>GET</td><td>/api/user/me/</td><td>Retrieve the authenticated user’s details</td></tr>
        <tr><td>PUT</td><td>/api/user/me/</td><td>Update the authenticated user’s details</td></tr>
        <tr><td>PATCH</td><td>/api/user/me/</td><td>Partial update of the authenticated user’s details</td></tr>
        <tr><td>POST</td><td>/api/user/token/</td><td>Create a new authentication token</td></tr>
    </tbody>
</table>

<h2>Setup Instructions</h2>
<ol>
    <li>Clone the repository</li>
    <pre><code>git clone https://github.com/yourusername/BackendPython.git</code></pre>
    <li>Navigate to the project directory</li>
    <pre><code>cd BackendPython</code></pre>
    <li>Create a virtual environment</li>
    <pre><code>python3 -m venv venv</code></pre>
    <li>Activate the virtual environment</li>
    <pre><code>source venv/bin/activate</code></pre>
    <li>Install dependencies</li>
    <pre><code>pip install -r requirements.txt</code></pre>
    <li>Apply migrations</li>
    <pre><code>python manage.py migrate</code></pre>
    <li>Run the development server</li>
    <pre><code>python manage.py runserver</code></pre>
</ol>

<h2>Authentication</h2>
<p>This API uses token-based authentication. 



</body>
</html>
