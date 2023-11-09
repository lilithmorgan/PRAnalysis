
resource "azurerm_resource_group" "pranalyzerrg" {
  name     = "PRAnalyzer"
  location = "East US"
}

resource "azurerm_virtual_network" "vnet" {
  name                = "PR-Analyzer-Net"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.pranalyzerrg.location
  resource_group_name = azurerm_resource_group.pranalyzerrg.name
}

resource "azurerm_subnet" "subnet" {
  name                 = "PR-Analyzer-subnet"
  resource_group_name  = azurerm_resource_group.pranalyzerrg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_network_interface" "nic" {
  name                = "PR-Analyzer-NIC"
  location            = azurerm_resource_group.pranalyzerrg.location
  resource_group_name = azurerm_resource_group.pranalyzerrg.name

  ip_configuration {
    name                          = "PR-Analyzer-Nic-Config"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.publicip.id
  }
}

resource "azurerm_public_ip" "publicip" {
  name                = "PR-Analyzer-Public-IP"
  location            = azurerm_resource_group.pranalyzerrg.location
  resource_group_name = azurerm_resource_group.pranalyzerrg.name
  allocation_method   = "Dynamic"
}

resource "azurerm_subnet_network_security_group_association" "association" {
  subnet_id                 = azurerm_subnet.subnet.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

resource "azurerm_network_security_group" "nsg" {
  name                = "PR-Analyzer-SG"
  location            = azurerm_resource_group.pranalyzerrg.location
  resource_group_name = azurerm_resource_group.pranalyzerrg.name

  security_rule {
    name                       = "SSH-VPN-1"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "PR-Analyzer_Webhook"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5001"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_linux_virtual_machine" "vm" {
  name                = "PR-Analyzer-Web"
  resource_group_name = azurerm_resource_group.pranalyzerrg.name
  location            = azurerm_resource_group.pranalyzerrg.location
  size                = "Standard_B1ms" // 83 reais por mes
  admin_username      = "adminuser"
  network_interface_ids = [azurerm_network_interface.nic.id]

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
    disk_size_gb         = 50
  }

    

  source_image_reference {
    publisher = "Debian"
    offer     = "debian-11"
    sku       = "11"
    version   = "latest"
  }

  admin_ssh_key {
    username   = "adminuser"
    public_key = file("Chaves/pranalyzer.pub")
  }
}

output "Servidor-PR-Analyzer-WEB-IP" {
  value = azurerm_public_ip.publicip.ip_address
}
