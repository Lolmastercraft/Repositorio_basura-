#PROYECTO FINAL

variable "key_pair_name" {
  description = "Nombre del par de llaves SSH"
  type        = string
  default     = "vockey"
}

variable "dynamodb_billing_mode" {
  description = "Modo de facturación de DynamoDB"
  type        = string
  default     = "PAY_PER_REQUEST"
}



#PROVEDOR
provider "aws" {
    region = "us-east-1"
}


variable "vpc_cidr" {
  description = "CIDR completo de la VPC (para reglas internas si lo necesitas)"
  type        = string
  default     = "10.10.0.0/20"
}


#VPC
resource "aws_vpc" "Pro_vpc" {
    cidr_block = "10.10.0.0/20"

    tags = {
        Name = "Proyecto_VPC"
    }
}

#SUBNET
resource "aws_subnet" "Pro_subnet_pub" {
    vpc_id = aws_vpc.Pro_vpc.id
    cidr_block = "10.10.0.0/24"
    map_public_ip_on_launch = true

    tags = {
        Name = "Proyecto_Subnet"
    }
}

#Gateway
resource "aws_internet_gateway" "Pro_igw" {
    vpc_id = aws_vpc.Pro_vpc.id

    tags = {
        Name = "Proyecto_IGW"
    }
}

#TABLAS DE RUTA
resource "aws_route_table" "Pro_tablaruta" {
    vpc_id = aws_vpc.Pro_vpc.id

    route {
        cidr_block = "0.0.0.0/0"
        gateway_id = aws_internet_gateway.Pro_igw.id
    }

    tags = {
        Name = "Proyecto_tablaruta"
    }
}

#ASOCIACION DE TABLAS DE RUTAS
resource "aws_route_table_association" "Pro_asociaciones" {
    subnet_id = aws_subnet.Pro_subnet_pub.id
    route_table_id = aws_route_table.Pro_tablaruta.id
}

#======================CREACION DE GRUPOS DE SEGURIDAD======================

resource "aws_security_group" "sg_jump" {
  name        = "SG_Jump"
  description = "Bastion / Jump Server"
  vpc_id      = aws_vpc.Pro_vpc.id

  #################################################
  # INGRESS
  #################################################

  # RDP (3389) – desde IP de administración
  ingress {
    description = "RDP desde admin"
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH (22) – desde IP de administración
  ingress {
    description = "SSH desde admin"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP (80) – opcional para pruebas, público
  ingress {
    description = "HTTP test"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS (443) – si expones algo vía TLS
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  #################################################
  # EGRESS (todo el tráfico saliente)
  #################################################
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "SG_Jump" }
}



############### SG LINUX##########################
resource "aws_security_group" "sg_linux_web" {
  name        = "SG_Linux_Web"
  description = "Web / API server"
  vpc_id      = aws_vpc.Pro_vpc.id

  #################################################
  # INGRESS
  #################################################

  # SSH (22) – solo desde el Jump
  ingress {
    description              = "SSH desde Jump"
    from_port                = 22
    to_port                  = 22
    protocol                 = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP público (80)
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS público (443)
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # API interna (5000) – solo desde Jump (o mismo SG si usas docker‑compose)
  ingress {
    description     = "Flask API"
    from_port       = 5000
    to_port         = 5000
    protocol        = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  #################################################
  # EGRESS
  #################################################
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "SG_Linux_Web" }
}


#======================CREACION DE INSTANCIAS======================

#INSTANCIA DE WinJS
resource "aws_instance" "WinJS" {
    ami = "ami-0c765d44cf1f25d26"
    instance_type = "t2.medium"

    subnet_id = aws_subnet.Pro_subnet_pub.id

    vpc_security_group_ids = [aws_security_group.sg_jump.id]


    associate_public_ip_address = false

    key_name = "vockey"

    tags = {
        Name = "Servidor WinJS"
    }

}

resource "aws_instance" "Linux_Web" {
  ami                    = "ami-084568db4383264d4"
  instance_type          = "t2.micro"
  subnet_id              = aws_subnet.Pro_subnet_pub.id
  vpc_security_group_ids = [aws_security_group.sg_linux_web.id]

  # Al usar una EIP no hace falta IP pública automática
  associate_public_ip_address = false

  key_name = "vockey"

  tags = {
    Name = "Servidor Linux Web"
  }
}


# Crear IP elástica
resource "aws_eip" "jump_eip" {
  instance = aws_instance.WinJS.id
  depends_on = [aws_internet_gateway.Pro_igw]
}

resource "aws_eip" "linux_eip" {
  instance = aws_instance.Linux_Web.id
  depends_on = [aws_internet_gateway.Pro_igw]
}


#OUTPUTS

output "elastic_ip_jump" {
  description = "IP elástica asignada al Jump Server"
  value       = aws_eip.jump_eip.public_ip
}

output "elastic_ip_linux" {
  description = "IP elástica asignada al servidor Linux"
  value       = aws_eip.linux_eip.public_ip
}
